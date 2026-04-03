import json
import sqlite3
import time
from pathlib import Path

DB_PATH = Path("data/search.db")
PAGES_FILE = Path("data/pages.jsonl")
INDEX_FILE = Path("data/index.json")
IDF_FILE = Path("data/idf.json")

PAGE_BATCH_SIZE = 2000
POSTING_BATCH_SIZE = 5000
IDF_BATCH_SIZE = 5000
LINK_BATCH_SIZE = 5000
LOG_EVERY = 10000
JSON_STREAM_CHUNK_SIZE = 1024 * 1024

DROP_SECONDARY_INDEXES_SQL = [
    "DROP INDEX IF EXISTS idx_pages_url",
    "DROP INDEX IF EXISTS idx_inverted_index_page_id",
    "DROP INDEX IF EXISTS idx_links_to_page",
]

CREATE_SECONDARY_INDEXES_SQL = [
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_pages_url ON pages(url)",
    "CREATE INDEX IF NOT EXISTS idx_inverted_index_page_id ON inverted_index(page_id)",
    "CREATE INDEX IF NOT EXISTS idx_links_to_page ON links(to_page)",
]


def log_progress(prefix: str, count: int, started_at: float) -> None:
    elapsed = max(time.perf_counter() - started_at, 0.001)
    print(f"{prefix} {count} | {count / elapsed:.2f}/s")


def batched_write(cursor: sqlite3.Cursor, sql: str, batch: list[tuple]) -> None:
    if batch:
        cursor.executemany(sql, batch)
        batch.clear()


def iter_pages(path: Path):
    next_page_id = 0

    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            raw_line = line.strip()
            if not raw_line:
                continue

            try:
                page = json.loads(raw_line)
            except json.JSONDecodeError:
                print(f"[load] skipped malformed page JSON at line {line_number}")
                continue

            if not isinstance(page, dict):
                continue

            yield next_page_id, page
            next_page_id += 1


def iter_json_object(path: Path, chunk_size: int = JSON_STREAM_CHUNK_SIZE):
    decoder = json.JSONDecoder()

    with path.open("r", encoding="utf-8") as handle:
        buffer = ""
        position = 0
        eof = False

        def compact_buffer() -> None:
            nonlocal buffer, position
            if position > chunk_size:
                buffer = buffer[position:]
                position = 0

        def read_more() -> bool:
            nonlocal buffer, position, eof
            if eof:
                return False

            chunk = handle.read(chunk_size)
            if not chunk:
                eof = True
                return False

            if position:
                buffer = buffer[position:]
                position = 0

            buffer += chunk
            return True

        def skip_whitespace() -> None:
            nonlocal position
            while True:
                while position < len(buffer) and buffer[position].isspace():
                    position += 1

                if position < len(buffer) or eof:
                    return

                read_more()

        def parse_value():
            nonlocal position
            while True:
                skip_whitespace()
                try:
                    value, new_position = decoder.raw_decode(buffer, position)
                    position = new_position
                    compact_buffer()
                    return value
                except json.JSONDecodeError:
                    if not read_more():
                        raise ValueError(f"Unexpected end of JSON while parsing {path}")

        def read_structural_char(expected_chars: str) -> str:
            nonlocal position
            while True:
                skip_whitespace()
                if position < len(buffer):
                    char = buffer[position]
                    if char not in expected_chars:
                        raise ValueError(
                            f"Expected one of {expected_chars!r} in {path}, found {char!r}"
                        )
                    position += 1
                    compact_buffer()
                    return char

                if not read_more():
                    raise ValueError(f"Unexpected end of JSON while parsing {path}")

        if not read_more():
            return

        read_structural_char("{")

        while True:
            skip_whitespace()

            while position >= len(buffer):
                if not read_more():
                    raise ValueError(f"Unexpected end of JSON while parsing {path}")
                skip_whitespace()

            if buffer[position] == "}":
                position += 1
                return

            key = parse_value()
            if not isinstance(key, str):
                raise ValueError(f"Expected string key in {path}")

            read_structural_char(":")
            value = parse_value()
            yield key, value

            delimiter = read_structural_char(",}")
            if delimiter == "}":
                return


def configure_fast_load_pragmas(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("PRAGMA journal_mode = OFF")
    conn.execute("PRAGMA synchronous = OFF")
    conn.execute("PRAGMA temp_store = MEMORY")
    conn.execute("PRAGMA cache_size = -200000")
    conn.execute("PRAGMA mmap_size = 268435456")
    conn.execute("PRAGMA locking_mode = EXCLUSIVE")


def restore_normal_pragmas(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA locking_mode = NORMAL")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA foreign_keys = ON")


def drop_secondary_indexes(cursor: sqlite3.Cursor) -> None:
    for sql in DROP_SECONDARY_INDEXES_SQL:
        cursor.execute(sql)


def create_secondary_indexes(cursor: sqlite3.Cursor) -> None:
    for sql in CREATE_SECONDARY_INDEXES_SQL:
        cursor.execute(sql)


def clear_tables(cursor: sqlite3.Cursor) -> None:
    cursor.execute("DELETE FROM links")
    cursor.execute("DELETE FROM inverted_index")
    cursor.execute("DELETE FROM idf")
    cursor.execute("DELETE FROM pages")


def load_pages_and_links(cursor: sqlite3.Cursor) -> tuple[int, dict[str, int]]:
    insert_pages_sql = """
        INSERT INTO pages (id, url, title, content, length, source)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    insert_links_sql = """
        INSERT OR IGNORE INTO links (from_page, to_page)
        VALUES (?, ?)
    """

    started_at = time.perf_counter()
    url_to_page_id: dict[str, int] = {}
    page_batch: list[tuple] = []
    inserted_pages = 0

    for page_id, page in iter_pages(PAGES_FILE):
        content = page.get("text", "")
        url = page.get("url", "")
        page_batch.append(
            (
                page_id,
                url,
                page.get("title", ""),
                content,
                len(content.split()),
                page.get("source", "other"),
            )
        )
        url_to_page_id[url] = page_id
        inserted_pages += 1

        if len(page_batch) >= PAGE_BATCH_SIZE:
            batched_write(cursor, insert_pages_sql, page_batch)

        if inserted_pages % LOG_EVERY == 0:
            log_progress("[load] pages:", inserted_pages, started_at)

    batched_write(cursor, insert_pages_sql, page_batch)
    log_progress("[load] pages:", inserted_pages, started_at)

    link_batch: list[tuple[int, int]] = []
    inserted_links = 0
    started_links_at = time.perf_counter()

    for page_id, page in iter_pages(PAGES_FILE):
        raw_links = page.get("links", [])
        if not raw_links:
            continue

        seen_targets = set()
        for target_url in raw_links:
            target_page_id = url_to_page_id.get(target_url)
            if target_page_id is None or target_page_id in seen_targets:
                continue

            seen_targets.add(target_page_id)
            link_batch.append((page_id, target_page_id))
            inserted_links += 1

            if len(link_batch) >= LINK_BATCH_SIZE:
                batched_write(cursor, insert_links_sql, link_batch)

        if inserted_links and inserted_links % LOG_EVERY == 0:
            log_progress("[load] links:", inserted_links, started_links_at)

    batched_write(cursor, insert_links_sql, link_batch)
    if inserted_links:
        log_progress("[load] links:", inserted_links, started_links_at)

    return inserted_pages, url_to_page_id


def load_postings(cursor: sqlite3.Cursor) -> int:
    insert_sql = """
        INSERT INTO inverted_index (word, page_id, frequency)
        VALUES (?, ?, ?)
    """

    started_at = time.perf_counter()
    posting_batch: list[tuple[str, int, int]] = []
    inserted_postings = 0

    for word, postings in iter_json_object(INDEX_FILE):
        for page_id, frequency in postings:
            posting_batch.append((word, int(page_id), int(frequency)))
            inserted_postings += 1

            if len(posting_batch) >= POSTING_BATCH_SIZE:
                batched_write(cursor, insert_sql, posting_batch)

            if inserted_postings % LOG_EVERY == 0:
                log_progress("[load] postings:", inserted_postings, started_at)

    batched_write(cursor, insert_sql, posting_batch)
    log_progress("[load] postings:", inserted_postings, started_at)
    return inserted_postings


def load_idf(cursor: sqlite3.Cursor) -> int:
    insert_sql = """
        INSERT INTO idf (word, idf)
        VALUES (?, ?)
    """

    started_at = time.perf_counter()
    idf_batch: list[tuple[str, float]] = []
    inserted_terms = 0

    for word, value in iter_json_object(IDF_FILE):
        idf_batch.append((word, float(value)))
        inserted_terms += 1

        if len(idf_batch) >= IDF_BATCH_SIZE:
            batched_write(cursor, insert_sql, idf_batch)

        if inserted_terms % LOG_EVERY == 0:
            log_progress("[load] idf:", inserted_terms, started_at)

    batched_write(cursor, insert_sql, idf_batch)
    log_progress("[load] idf:", inserted_terms, started_at)
    return inserted_terms


def main() -> None:
    overall_started_at = time.perf_counter()
    conn = sqlite3.connect(DB_PATH, isolation_level=None)
    cursor = conn.cursor()

    try:
        configure_fast_load_pragmas(conn)

        cursor.execute("BEGIN IMMEDIATE")
        drop_secondary_indexes(cursor)
        clear_tables(cursor)

        inserted_pages, _url_to_page_id = load_pages_and_links(cursor)
        inserted_postings = load_postings(cursor)
        inserted_terms = load_idf(cursor)

        create_secondary_indexes(cursor)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        restore_normal_pragmas(conn)
        conn.close()

    elapsed = max(time.perf_counter() - overall_started_at, 0.001)
    print("\n[load] complete")
    print(f"[load] pages={inserted_pages}")
    print(f"[load] postings={inserted_postings}")
    print(f"[load] idf_terms={inserted_terms}")
    print(f"[load] elapsed={elapsed:.2f}s")


if __name__ == "__main__":
    main()
