import json
import nltk
nltk.download("stopwords")
nltk.download("punkt")
nltk.download("punkt_tab")
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

with open("data/index.json","r",encoding="utf-8") as f:
    inverted_index = json.load(f)

with open("data/pages.json","r",encoding="utf-8") as f:
    pages = json.load(f)

with open("data/idf.json", "r", encoding="utf-8") as f:
    idf = json.load(f)

stop_words = set(stopwords.words("english"))

def search(query):
    if query.strip() == "":
        print("Please Enter your Something")
        return []
        
    query_words = word_tokenize(query.lower())
    query_words = [w for w in query_words if w.isalnum()]

    page_score = {}
   
    for word in query_words:
        if word in inverted_index:
            for page_id,count in inverted_index[word]:
                page_id = int(page_id)
                page_score[page_id] = page_score.get(page_id,0) + count * idf[word]
    
    results = []
    seen = set()

    for page_id, score in page_score.items():
        page = pages[page_id]
        clean_url = page["url"].split("#")[0]

        title = page["title"].lower()
        boost = 0

        for word in query_words:
            if word in title:
                boost +=5
        final_score = score +boost

        if final_score>2 and clean_url not in seen:
            results.append((final_score,page["title"], clean_url))
            seen.add(clean_url)

    results.sort(reverse=True)
    return results




