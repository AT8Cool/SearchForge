import sqlite3

conn = sqlite3.connect('data/search.db')
cur = conn.cursor()

cur.execute(""" 
    CREATE TABLE IF NOT EXISTS pages(
        id INTEGER PRIMARY KEY,
        url TEXT UNIQUE,
        title TEXT,
        content TEXT,
        length INTEGER,
        source TEXT,
        views INTEGER DEFAULT 0,
        published_date TEXT
    )       
""")

cur.execute("""
    CREATE TABLE IF NOT EXISTS inverted_index(
        word TEXT,
        page_id INTEGER,
        frequency INTEGER
    )
""")

cur.execute("""
    CREATE TABLE IF NOT EXISTS idf(
        word TEXT PRIMARY KEY,
        idf REAL
    )
""")

cur.execute("CREATE INDEX IF NOT EXISTS idx_word ON inverted_index(word)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_page_id ON inverted_index(page_id)")

conn.commit()
conn.close()

print("DB created (with source support)")