# import json

# count = 0
# with open("data/pages.json","r",encoding='utf-8') as f:
#     f = json.load(f)

# for pages in f:
#     count +=1

# print(count)

# import sqlite3

# conn = sqlite3.connect('data/search.db')
# cur = conn.cursor()

# cur.execute("PRAGMA table_info(pages);")
# print(cur.fetchall())

import sqlite3

conn = sqlite3.connect('data/search.db')
cur = conn.cursor()

cur.execute("SELECT source, COUNT(*) FROM pages GROUP BY source")
print(cur.fetchall())

conn.close()