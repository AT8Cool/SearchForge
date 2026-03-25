import json
import math
from collections import defaultdict
from collections import Counter
from nltk.tokenize import word_tokenize
from nltk.corpus import  stopwords

stop_words = set(stopwords.words("english"))



with open("data/pages.json","r",encoding ="utf-8")as f:
    pages = json.load(f)

inverted_index = defaultdict(list)

for i,page in enumerate(pages):
    text = page["text"].lower()
    words = word_tokenize(text)
    words = [w for w in words if w.isalnum() and w not in stop_words]

    word_count = Counter(words)
    for word,count in word_count.items():
            inverted_index[word].append((i,count))

with open("data/index.json","w",encoding ="utf-8")as f:
    json.dump(inverted_index,f)

N = len(pages)
idf = {}

for word,postings in inverted_index.items():
     df = len(postings)
     idf[word] = math.log(N / (1+df))

with open("data/idf.json","w",encoding="utf-8") as f:
     json.dump(idf,f)    

print("index done done done")