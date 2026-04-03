import re
import sqlite3
import threading
from collections import Counter, OrderedDict, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse, urlunparse

from app.core.settings import get_db_path

DB_PATH = get_db_path()
SQLITE_PARAM_LIMIT = 900
SQLITE_CACHE_SIZE = -200000
SQLITE_MMAP_SIZE = 268435456
PAGE_FEATURE_CACHE_SIZE = 2048

TOKEN_RE = re.compile(r"[a-z0-9]+")
NON_ALNUM_RE = re.compile(r"[^a-z0-9\s]+")
WHITESPACE_RE = re.compile(r"\s+")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?]) +")
BANNED_URL_MARKERS = ("Talk:", "File:", "Help:", "Category:")

STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "ain", "all", "am",
    "an", "and", "any", "are", "aren", "as", "at", "be", "because", "been",
    "before", "being", "below", "between", "both", "but", "by", "can",
    "couldn", "d", "did", "didn", "do", "does", "doesn", "doing", "don",
    "down", "during", "each", "few", "for", "from", "further", "had",
    "hadn", "has", "hasn", "have", "haven", "having", "he", "her", "here",
    "hers", "herself", "him", "himself", "his", "how", "i", "if", "in",
    "into", "is", "isn", "it", "its", "itself", "just", "ll", "m", "ma",
    "me", "mightn", "more", "most", "mustn", "my", "myself", "needn", "no",
    "nor", "not", "now", "o", "of", "off", "on", "once", "only", "or",
    "other", "our", "ours", "ourselves", "out", "over", "own", "re", "s",
    "same", "shan", "she", "should", "shouldn", "so", "some", "such", "t",
    "than", "that", "the", "their", "theirs", "them", "themselves", "then",
    "there", "these", "they", "this", "those", "through", "to", "too",
    "under", "until", "up", "ve", "very", "was", "wasn", "we", "were",
    "weren", "what", "when", "where", "which", "while", "who", "whom",
    "why", "will", "with", "won", "wouldn", "y", "you", "your", "yours",
    "yourself", "yourselves",
}

k = 1.5
b = 0.75
BM25_NUMERATOR_FACTOR = k + 1.0

SOURCE_WEIGHTS = {
    "wikipedia": 1.0,
    "encyclopedia": 0.95,
    "science": 0.95,
    "health": 0.95,
    "mdn": 0.9,
    "docs": 0.9,
    "gfg": 0.85,
    "qa": 0.8,
    "finance": 0.75,
    "news": 0.65,
    "medium": 0.6,
    "other": 0.5,
}


def normalize_text(text: str) -> str:
    cleaned = NON_ALNUM_RE.sub(" ", text.lower())
    return WHITESPACE_RE.sub(" ", cleaned).strip()


def tokenize_query(query: str) -> list[str]:
    raw_words = TOKEN_RE.findall(query.lower())
    filtered_words = [word for word in raw_words if word not in STOP_WORDS]
    return filtered_words if filtered_words else raw_words


def chunked(values: Iterable[int], size: int):
    batch = []
    for value in values:
        batch.append(value)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def canonicalize_url(url: str) -> str:
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    if netloc.startswith("www."):
        netloc = netloc[4:]

    path = parsed.path.rstrip("/")
    return urlunparse((scheme, netloc, path, "", "", ""))


def generate_snippet(content: str, query_words: list[str], length: int = 200) -> str:
    if not content:
        return ""

    sentences = SENTENCE_SPLIT_RE.split(content)
    best_sentence = ""
    max_matches = 0

    for sentence in sentences:
        sentence_lower = sentence.lower()
        match_count = sum(1 for word in query_words if word in sentence_lower)

        if match_count > max_matches:
            max_matches = match_count
            best_sentence = sentence

    if best_sentence:
        return best_sentence.strip()

    snippet = content[:length].strip()
    return snippet + "..." if len(content) > length else snippet


@dataclass(slots=True)
class PreparedPage:
    clean_url: str
    title_clean: str
    content_clean: str
    title_words: frozenset[str]
    content_words: frozenset[str]


class SearchRuntime:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._thread_local = threading.local()
        self._page_feature_cache: OrderedDict[int, PreparedPage] = OrderedDict()
        self._page_feature_lock = threading.Lock()
        self.idf_cache: dict[str, float] = {}
        self.page_lengths: dict[int, int] = {}
        self.avgdl = 1.0
        self._warm_static_cache()

    def _create_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            cached_statements=512,
        )
        conn.execute("PRAGMA query_only = ON")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA temp_store = MEMORY")
        conn.execute(f"PRAGMA cache_size = {SQLITE_CACHE_SIZE}")
        conn.execute(f"PRAGMA mmap_size = {SQLITE_MMAP_SIZE}")
        return conn

    def _warm_static_cache(self) -> None:
        conn = self._create_connection()
        try:
            page_lengths: dict[int, int] = {}
            total_length = 0

            for page_id, length in conn.execute("SELECT id, length FROM pages"):
                page_lengths[page_id] = length
                total_length += length

            self.page_lengths = page_lengths
            self.avgdl = (total_length / len(page_lengths)) if page_lengths else 1.0
            self.idf_cache = dict(conn.execute("SELECT word, idf FROM idf"))
        finally:
            conn.close()

    def connection(self) -> sqlite3.Connection:
        conn = getattr(self._thread_local, "conn", None)
        if conn is None:
            conn = self._create_connection()
            self._thread_local.conn = conn
        return conn

    def fetch_postings(self, terms: list[str]) -> tuple[defaultdict[str, list[tuple[int, int]]], set[int]]:
        placeholders = ",".join("?" for _ in terms)
        sql = (
            "SELECT word, page_id, frequency "
            f"FROM inverted_index WHERE word IN ({placeholders})"
        )

        postings_by_word: defaultdict[str, list[tuple[int, int]]] = defaultdict(list)
        page_ids: set[int] = set()

        for word, page_id, frequency in self.connection().execute(sql, terms):
            postings_by_word[word].append((page_id, frequency))
            page_ids.add(page_id)

        return postings_by_word, page_ids

    def fetch_pages(self, page_ids: Iterable[int]) -> dict[int, tuple[str, str, str, str, float]]:
        page_rows: dict[int, tuple[str, str, str, str, float]] = {}

        for page_batch in chunked(page_ids, SQLITE_PARAM_LIMIT):
            placeholders = ",".join("?" for _ in page_batch)
            sql = (
                "SELECT id, title, url, content, source, pagerank "
                f"FROM pages WHERE id IN ({placeholders})"
            )

            for page_id, title, url, content, source, pagerank in self.connection().execute(sql, page_batch):
                page_rows[page_id] = (title, url, content, source, pagerank)

        return page_rows

    def prepare_page(self, page_id: int, title: str, url: str, content: str) -> PreparedPage:
        with self._page_feature_lock:
            cached = self._page_feature_cache.get(page_id)
            if cached is not None:
                self._page_feature_cache.move_to_end(page_id)
                return cached

        title_clean = normalize_text(title)
        content_clean = normalize_text(content)
        prepared = PreparedPage(
            clean_url=canonicalize_url(url),
            title_clean=title_clean,
            content_clean=content_clean,
            title_words=frozenset(title_clean.split()),
            content_words=frozenset(content_clean.split()),
        )

        with self._page_feature_lock:
            self._page_feature_cache[page_id] = prepared
            self._page_feature_cache.move_to_end(page_id)
            if len(self._page_feature_cache) > PAGE_FEATURE_CACHE_SIZE:
                self._page_feature_cache.popitem(last=False)

        return prepared


try:
    _runtime: SearchRuntime | None = SearchRuntime(DB_PATH)
except sqlite3.Error:
    _runtime = None

_runtime_lock = threading.Lock()


def get_runtime() -> SearchRuntime:
    global _runtime

    if _runtime is None:
        with _runtime_lock:
            if _runtime is None:
                _runtime = SearchRuntime(DB_PATH)
    return _runtime


def refresh_search_cache() -> None:
    global _runtime

    with _runtime_lock:
        _runtime = SearchRuntime(DB_PATH)


def search(query: str):
    if not query.strip():
        return []

    runtime = get_runtime()
    query_words = tokenize_query(query)
    if not query_words:
        return []

    query_lower = query.lower()
    is_what_is_query = "what is" in query_lower

    if is_what_is_query:
        preferred_sources = {"wikipedia"}
    elif "how" in query_lower:
        preferred_sources = {"gfg", "stackoverflow"}
    else:
        preferred_sources = set()

    query_term_counts = Counter(query_words)
    searchable_terms = [word for word in query_term_counts if word in runtime.idf_cache]
    if not searchable_terms:
        return []

    postings_by_word, _page_ids = runtime.fetch_postings(searchable_terms)
    if not postings_by_word:
        return []

    avgdl = runtime.avgdl or 1.0
    length_scale = k * b / avgdl
    base_denominator = k * (1.0 - b)
    page_lengths = runtime.page_lengths
    page_score: defaultdict[int, float] = defaultdict(float)

    for word, query_count in query_term_counts.items():
        postings = postings_by_word.get(word)
        if not postings:
            continue

        bm25_multiplier = runtime.idf_cache[word] * query_count

        for page_id, freq in postings:
            document_length = page_lengths.get(page_id, avgdl)
            denominator = freq + base_denominator + (length_scale * document_length)
            page_score[page_id] += bm25_multiplier * ((freq * BM25_NUMERATOR_FACTOR) / denominator)

    if not page_score:
        return []

    page_data = runtime.fetch_pages(page_score.keys())
    if not page_data:
        return []

    query_clean = normalize_text(query)
    unique_query_words = tuple(query_term_counts)
    results = []
    seen_urls = set()

    for page_id, base_score in page_score.items():
        page_row = page_data.get(page_id)
        if page_row is None:
            continue

        title, url, content, source, pagerank = page_row

        if any(marker in url for marker in BANNED_URL_MARKERS):
            continue

        prepared = runtime.prepare_page(page_id, title, url, content)
        clean_url = prepared.clean_url
        if clean_url in seen_urls:
            continue

        final_score = base_score
        source_weight = SOURCE_WEIGHTS.get(source, 0.5)
        final_score *= (0.7 + 0.3 * source_weight)

        if is_what_is_query and source == "wikipedia":
            final_score *= 1.5

        if is_what_is_query and source in ["gfg", "stackoverflow"]:
            final_score *= 0.8

        if not any(word in prepared.title_words for word in unique_query_words):
            final_score *= 0.95

        if source in preferred_sources:
            final_score *= 1.3

        if source == "other":
            final_score *= 0.7

        # Apply a light authority boost when PageRank has been computed.
        if pagerank > 0:
            final_score *= (1.0 + min(pagerank, 1.0) * 0.15)

        match_count = sum(
            count for word, count in query_term_counts.items() if word in prepared.title_words
        )
        if match_count > 0:
            final_score *= (1 + 0.2 * match_count)

        if query_clean in prepared.title_clean:
            final_score *= 1.5
        elif query_clean in prepared.content_clean:
            final_score *= 1.2

        if all(word in prepared.content_words for word in unique_query_words):
            final_score *= 1.2

        if any(word in clean_url for word in unique_query_words):
            final_score *= 1.1

        snippet = generate_snippet(content, query_words)

        if final_score < 0.3:
            continue

        results.append(
            {
                "score": final_score,
                "title": title,
                "url": clean_url,
                "snippet": snippet,
            }
        )
        seen_urls.add(clean_url)

    results.sort(key=lambda item: item["score"], reverse=True)
    return results


def run_search(query: str):
    return search(query)
