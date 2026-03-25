from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.search import search


app = FastAPI()

app.add_middleware(CORSMiddleware,
                   allow_origins = ["*"],
                   allow_credentials=True,
                   allow_methods=["*"],
                   allow_headers=["*"])

@app.get("/")
def root():
    return {"message":"API is running"}

@app.get("/search")
def search_api(q:str= "", page:int = 1, limit:int=10):
    if not q.strip():
        return {"results": []}

    all_results = search(q)

    total = len(all_results)
    start = (page-1) *limit
    end = start + limit


    paginated = all_results[start:end]


    formatted = [
        {
            "title":title,
            "url":url,
            "score":score
        }
        for score, title, url in paginated
    ]

    return {"results":formatted,"total":total}