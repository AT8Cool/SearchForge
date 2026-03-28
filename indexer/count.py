import json

count = 0
with open("data/pages.json","r",encoding='utf-8') as f:
    f = json.load(f)

for pages in f:
    count +=1

print(count)
