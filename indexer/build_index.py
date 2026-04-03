import argparse
import json
import math
import os
import re
import shutil
import time
import zlib
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from itertools import repeat
from pathlib import Path
from typing import Iterator

DATA_DIR = Path("data")
INPUT_FILE = DATA_DIR / "pages.jsonl"
INDEX_FILE = DATA_DIR / "index.json"
IDF_FILE = DATA_DIR / "idf.json"
TEMP_DIR = DATA_DIR / "index_shards"

DEFAULT_WORKERS = max(1, (os.cpu_count() or 2) - 1)
DEFAULT_CHUNK_SIZE = 400
DEFAULT_SHARD_COUNT = 256
DEFAULT_LOG_EVERY = 5_000

TOKEN_RE = re.compile(r"[a-z0-9]+")
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


@dataclass(slots=True)
class BuildConfig:
    input_file: Path
    index_file: Path
    idf_file: Path
    temp_dir: Path
    workers: int
    chunk_size: int
    shard_count: int
    log_every: int


def tokenize(text: str) -> list[str]:
    return [token for token in TOKEN_RE.findall(text.lower()) if token not in STOP_WORDS]


def shard_for_term(term: str, shard_count: int) -> int:
    return zlib.crc32(term.encode("utf-8")) % shard_count


def chunk_documents(input_file: Path, chunk_size: int) -> Iterator[list[tuple[int, str]]]:
    batch: list[tuple[int, str]] = []
    next_doc_id = 0

    with input_file.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            raw_line = line.strip()
            if not raw_line:
                continue

            try:
                page = json.loads(raw_line)
            except json.JSONDecodeError:
                print(f"[index] skipped malformed JSON at line {line_number}")
                continue

            text = page.get("text", "") if isinstance(page, dict) else ""
            batch.append((next_doc_id, text))
            next_doc_id += 1

            if len(batch) >= chunk_size:
                yield batch
                batch = []

    if batch:
        yield batch


def process_chunk(docs: list[tuple[int, str]], shard_count: int) -> tuple[int, int, dict[int, str]]:
    shard_buffers: defaultdict[int, list[str]] = defaultdict(list)
    posting_count = 0

    for doc_id, text in docs:
        word_count = Counter(tokenize(text))
        posting_count += len(word_count)

        for word, freq in word_count.items():
            shard_id = shard_for_term(word, shard_count)
            shard_buffers[shard_id].append(f"{word}\t{doc_id}\t{freq}\n")

    payloads = {shard_id: "".join(lines) for shard_id, lines in shard_buffers.items()}
    return len(docs), posting_count, payloads


def prepare_temp_dir(temp_dir: Path) -> None:
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)


def open_shard_handles(temp_dir: Path, shard_count: int) -> list:
    return [
        (temp_dir / f"shard_{shard_id:03d}.tsv").open("a", encoding="utf-8")
        for shard_id in range(shard_count)
    ]


def write_shard_payloads(handles: list, payloads: dict[int, str]) -> None:
    for shard_id, text in payloads.items():
        handles[shard_id].write(text)


def log_progress(prefix: str, value: int, started_at: float, extra: str = "") -> None:
    elapsed = max(time.perf_counter() - started_at, 0.001)
    rate = value / elapsed
    suffix = f" | {extra}" if extra else ""
    print(f"{prefix} {value} | {rate:.2f}/s{suffix}")


def build_shards(config: BuildConfig) -> tuple[int, int]:
    prepare_temp_dir(config.temp_dir)
    total_docs = 0
    total_postings = 0
    started_at = time.perf_counter()

    shard_handles = open_shard_handles(config.temp_dir, config.shard_count)
    try:
        chunk_iter = chunk_documents(config.input_file, config.chunk_size)

        if config.workers == 1:
            result_iter = (process_chunk(chunk, config.shard_count) for chunk in chunk_iter)
        else:
            with ProcessPoolExecutor(max_workers=config.workers) as executor:
                result_iter = executor.map(
                    process_chunk,
                    chunk_iter,
                    repeat(config.shard_count),
                    chunksize=1,
                )

                for docs_in_chunk, postings_in_chunk, payloads in result_iter:
                    total_docs += docs_in_chunk
                    total_postings += postings_in_chunk
                    write_shard_payloads(shard_handles, payloads)

                    if config.log_every and total_docs % config.log_every < docs_in_chunk:
                        log_progress(
                            "[index] documents:",
                            total_docs,
                            started_at,
                            extra=f"postings={total_postings}",
                        )

                return total_docs, total_postings

        for docs_in_chunk, postings_in_chunk, payloads in result_iter:
            total_docs += docs_in_chunk
            total_postings += postings_in_chunk
            write_shard_payloads(shard_handles, payloads)

            if config.log_every and total_docs % config.log_every < docs_in_chunk:
                log_progress(
                    "[index] documents:",
                    total_docs,
                    started_at,
                    extra=f"postings={total_postings}",
                )
    finally:
        for handle in shard_handles:
            handle.close()

    return total_docs, total_postings


def read_shard(shard_path: Path) -> defaultdict[str, list[list[int]]]:
    postings_by_term: defaultdict[str, list[list[int]]] = defaultdict(list)

    with shard_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            word, doc_id, freq = line.rstrip("\n").split("\t")
            postings_by_term[word].append([int(doc_id), int(freq)])

    return postings_by_term


def stream_json_entry(handle, key: str, value, first_entry: bool) -> bool:
    if not first_entry:
        handle.write(",")

    json.dump(key, handle, ensure_ascii=False)
    handle.write(":")
    json.dump(value, handle, ensure_ascii=False, separators=(",", ":"))
    return False


def merge_shards(config: BuildConfig, total_docs: int) -> tuple[int, int]:
    started_at = time.perf_counter()
    shard_paths = [config.temp_dir / f"shard_{shard_id:03d}.tsv" for shard_id in range(config.shard_count)]

    if total_docs == 0:
        config.index_file.write_text("{}", encoding="utf-8")
        config.idf_file.write_text("{}", encoding="utf-8")
        return 0, 0

    total_terms = 0
    merged_postings = 0
    first_index_entry = True
    first_idf_entry = True

    with config.index_file.open("w", encoding="utf-8") as index_handle:
        with config.idf_file.open("w", encoding="utf-8") as idf_handle:
            index_handle.write("{")
            idf_handle.write("{")

            for shard_number, shard_path in enumerate(shard_paths, start=1):
                if not shard_path.exists() or shard_path.stat().st_size == 0:
                    continue

                postings_by_term = read_shard(shard_path)
                shard_term_count = len(postings_by_term)
                total_terms += shard_term_count

                for word in sorted(postings_by_term):
                    postings = postings_by_term[word]
                    merged_postings += len(postings)
                    first_index_entry = stream_json_entry(
                        index_handle,
                        word,
                        postings,
                        first_index_entry,
                    )
                    first_idf_entry = stream_json_entry(
                        idf_handle,
                        word,
                        math.log(total_docs / (1 + len(postings))),
                        first_idf_entry,
                    )

                print(
                    f"[merge] shard {shard_number}/{config.shard_count} "
                    f"terms={shard_term_count} total_terms={total_terms}"
                )

                shard_path.unlink()

            index_handle.write("}")
            idf_handle.write("}")

    log_progress("[merge] terms:", total_terms, started_at, extra=f"postings={merged_postings}")
    shutil.rmtree(config.temp_dir, ignore_errors=True)
    return total_terms, merged_postings


def parse_args() -> BuildConfig:
    parser = argparse.ArgumentParser(description="Stream and build an inverted index from pages.jsonl.")
    parser.add_argument("--input", type=Path, default=INPUT_FILE)
    parser.add_argument("--index-output", type=Path, default=INDEX_FILE)
    parser.add_argument("--idf-output", type=Path, default=IDF_FILE)
    parser.add_argument("--temp-dir", type=Path, default=TEMP_DIR)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    parser.add_argument("--shards", type=int, default=DEFAULT_SHARD_COUNT)
    parser.add_argument("--log-every", type=int, default=DEFAULT_LOG_EVERY)
    args = parser.parse_args()

    return BuildConfig(
        input_file=args.input,
        index_file=args.index_output,
        idf_file=args.idf_output,
        temp_dir=args.temp_dir,
        workers=max(1, args.workers),
        chunk_size=max(1, args.chunk_size),
        shard_count=max(1, args.shards),
        log_every=max(0, args.log_every),
    )


def main() -> None:
    config = parse_args()
    overall_started_at = time.perf_counter()
    config.index_file.parent.mkdir(parents=True, exist_ok=True)
    config.idf_file.parent.mkdir(parents=True, exist_ok=True)

    print(
        "[index] starting "
        f"workers={config.workers} chunk_size={config.chunk_size} shards={config.shard_count}"
    )

    total_docs, total_postings = build_shards(config)
    total_terms, merged_postings = merge_shards(config, total_docs)
    elapsed = max(time.perf_counter() - overall_started_at, 0.001)

    print("\n[index] complete")
    print(f"[index] documents={total_docs}")
    print(f"[index] unique_terms={total_terms}")
    print(f"[index] postings_emitted={total_postings}")
    print(f"[index] postings_merged={merged_postings}")
    print(f"[index] elapsed={elapsed:.2f}s")


if __name__ == "__main__":
    main()
