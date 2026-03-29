import json
import sqlite3

conn = sqlite3.connect('data/search.db')
cur = conn.cursor()

with open("data/pages.json","r",encoding="utf-8") as f:
    pages = json.load(f)

with open("data/index.json","r",encoding="utf-8") as f:
    index = json.load(f)

with open("data/idf.json","r",encoding="utf-8") as f:
    idf = json.load(f)

# insert pages ✅
for i, page in enumerate(pages):
    content = page.get("text", "")
    cur.execute("""
        INSERT OR IGNORE INTO pages (id, url, title, content, length, source)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (i, 
          page["url"], 
          page["title"], 
          content, 
          len(content.split()), 
          page.get("source","other"))) 

# insert inverted index
for word, postings in index.items():
    for page_id, freq in postings:
        cur.execute("""
            INSERT INTO inverted_index(word,page_id,frequency)
            VALUES(?,?,?)
        """,(word,int(page_id),freq))

# insert idf
for word, val in idf.items():
    cur.execute("""
        INSERT OR REPLACE INTO idf(word,idf)
        VALUES(?,?)
    """,(word,val))

conn.commit()
conn.close()

print("Data migrated to SQLite")