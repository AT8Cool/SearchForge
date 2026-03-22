import json
import nltk
nltk.download("stopwords")
nltk.download("punkt")
nltk.download("punkt_tab")
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

with open("pages.json","r",encoding="utf-8") as f:
    pages = json.load(f)

stop_words = set(stopwords.words("english"))

def search(query):
    if query == "":
        print("Please Enter your Something")
        return []
        
    
    results = []
    query_words = word_tokenize(query.lower())
    query_words = [word for word in query_words if word.isalnum() and word not in stop_words]

    for page in pages:
        text = page["text"].lower()
        words = word_tokenize(text)

        words = [w for w in words if w.isalnum() and w not in stop_words]

        score = 0
        for word in query_words:
            score += text.count(word)

        if score > 1:
            results.append((score,page["title"],page["url"]))

        #sort by frequency (basic ranking)
    results.sort(reverse=True)

    return results[:10]


def enter_query():
    query = input("Search :")
    results = search(query)
    
    for score, title,url in results:
        print(f"{title} -> {url} -> (score:{score})")
    return


enter_query()