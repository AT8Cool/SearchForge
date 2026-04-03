import sqlite3
from pathlib import Path

DB_PATH = Path("data/search.db")


def configure_connection(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA temp_store = MEMORY")
    conn.execute("PRAGMA cache_size = -200000")
    conn.execute("PRAGMA mmap_size = 268435456")


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    configure_connection(conn)
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS pages (
            id INTEGER PRIMARY KEY,
            url TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            content TEXT NOT NULL DEFAULT '',
            length INTEGER NOT NULL CHECK (length >= 0),
            source TEXT NOT NULL DEFAULT 'other',
            views INTEGER NOT NULL DEFAULT 0 CHECK (views >= 0),
            published_date TEXT,
            pagerank REAL NOT NULL DEFAULT 0.0 CHECK (pagerank >= 0.0)
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_pages_url ON pages(url);

        CREATE TABLE IF NOT EXISTS inverted_index (
            word TEXT NOT NULL,
            page_id INTEGER NOT NULL,
            frequency INTEGER NOT NULL CHECK (frequency > 0),
            PRIMARY KEY (word, page_id),
            FOREIGN KEY (page_id) REFERENCES pages(id) ON DELETE CASCADE
        ) WITHOUT ROWID;

        CREATE INDEX IF NOT EXISTS idx_inverted_index_page_id ON inverted_index(page_id);

        CREATE TABLE IF NOT EXISTS idf (
            word TEXT PRIMARY KEY,
            idf REAL NOT NULL
        ) WITHOUT ROWID;

        CREATE TABLE IF NOT EXISTS links (
            from_page INTEGER NOT NULL,
            to_page INTEGER NOT NULL,
            PRIMARY KEY (from_page, to_page),
            FOREIGN KEY (from_page) REFERENCES pages(id) ON DELETE CASCADE,
            FOREIGN KEY (to_page) REFERENCES pages(id) ON DELETE CASCADE
        ) WITHOUT ROWID;

        CREATE INDEX IF NOT EXISTS idx_links_to_page ON links(to_page);
        """
    )

    conn.commit()
    conn.close()

    print("DB created with BM25-friendly schema and explicit pagerank support")


if __name__ == "__main__":
    main()
