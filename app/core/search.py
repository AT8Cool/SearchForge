import sqlite3
import re
from urllib.parse import urlparse, urlunparse
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# --- DB connection ---
conn = sqlite3.connect("data/search.db", check_same_thread=False)
cur = conn.cursor()

# --- Config ---
stop_words = set(stopwords.words("english"))

cur.execute("SELECT AVG(length) FROM pages")
avgdl = cur.fetchone()[0] or 1

k = 1.5
b = 0.75


# --- URL cleanup ---
def canonicalize_url(url):
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    if netloc.startswith("www."):
        netloc = netloc[4:]

    path = parsed.path.rstrip("/")

    return urlunparse((scheme, netloc, path, "", "", ""))


# --- Snippet ---
def generate_snippet(content, query_words, length=200):
    if not content:
        return ""

    sentences = re.split(r'(?<=[.!?]) +', content)

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


# --- SEARCH ---
def search(query):
    if not query.strip():
        return []

    raw_words = word_tokenize(query.lower())
    raw_words = [w for w in raw_words if w.isalnum()]
    filtered_words = [w for w in raw_words if w not in stop_words]

    query_words = filtered_words if filtered_words else raw_words

    if not query_words:
        return []

    # --- batch fetch postings ---
    placeholders = ",".join("?" for _ in query_words)

    cur.execute(
        f"SELECT word, page_id, frequency FROM inverted_index WHERE word IN ({placeholders})",
        query_words
    )
    rows = cur.fetchall()

    postings_dict = {}
    page_ids_set = set()

    for word, page_id, freq in rows:
        postings_dict.setdefault(word, []).append((page_id, freq))
        page_ids_set.add(page_id)

    if not postings_dict:
        return []

    # --- batch fetch idf ---
    cur.execute(
        f"SELECT word, idf FROM idf WHERE word IN ({placeholders})",
        query_words
    )
    idf_dict = dict(cur.fetchall())

    # --- batch fetch page lengths ---
    page_ids = list(page_ids_set)
    placeholders_pages = ",".join("?" for _ in page_ids)

    cur.execute(
        f"SELECT id, length FROM pages WHERE id IN ({placeholders_pages})",
        page_ids
    )
    length_dict = dict(cur.fetchall())

    # --- BM25 ---
    page_score = {}

    for word in query_words:
        if word not in postings_dict or word not in idf_dict:
            continue

        idf_val = idf_dict[word]

        for page_id, freq in postings_dict[word]:
            dl = length_dict.get(page_id, avgdl)
            tf = freq

            bm25 = idf_val * (
                (tf * (k + 1)) /
                (tf + k * (1 - b + b * (dl / avgdl)))
            )

            page_score[page_id] = page_score.get(page_id, 0.0) + bm25

    if not page_score:
        return []

    # --- batch fetch page data ---
    cur.execute(
        f"SELECT id, title, url, content FROM pages WHERE id IN ({placeholders_pages})",
        page_ids
    )
    page_data = {row[0]: row[1:] for row in cur.fetchall()}

    results = []
    seen = set()

    full_query = " ".join(query_words)

    for page_id, base_score in page_score.items():
        if page_id not in page_data:
            continue

        title, url, content = page_data[page_id]

        # (keep your original logic exactly)
        if any(x in url for x in ["Talk:", "File:", "Help:", "Category:"]):
            continue

        clean_url = canonicalize_url(url)

        if clean_url in seen:
            continue

        title_lower = title.lower()
        content_lower = content.lower()

        title_clean = re.sub(r'[^a-z0-9\s]', ' ', title_lower)
        content_clean = re.sub(r'[^a-z0-9\s]', ' ', content_lower)

        title_words = set(title_clean.split())
        content_words = set(content_clean.split())

        final_score = base_score

        match_count = sum(1 for w in query_words if w in title_words)
        if match_count > 0:
            final_score *= (1 + 0.2 * match_count)

        if full_query in title_clean:
            final_score *= 1.8
        elif full_query in content_clean:
            final_score *= 1.3

        if all(w in content_words for w in query_words):
            final_score *= 1.2

        snippet = generate_snippet(content, query_words)

        results.append({
            "score": final_score,
            "title": title,
            "url": clean_url,
            "snippet": snippet
        })

        seen.add(clean_url)

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def run_search(query):
    return search(query)