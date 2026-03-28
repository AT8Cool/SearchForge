from fastapi import FastAPI,Query
from fastapi.middleware.cors import CORSMiddleware
from app.core.search import run_search
from time import time

_cache = {}
_cache_time = {}
CACHE_TTL = 600

app = FastAPI()

app.add_middleware(CORSMiddleware,
                   allow_origins = ["*"],
                   allow_credentials=True,
                   allow_methods=["*"],
                   allow_headers=["*"])

@app.get("/")
def root():
    return {"message":"API is running"}

def cached_search(query: str):
    now = time()
    if query in _cache and (now - _cache_time[query]) < CACHE_TTL:
        return _cache[query]
    result = tuple(run_search(query))
    _cache[query] = result
    _cache_time[query] = now
    return result

@app.get("/search")
def search_api(q:str= 
               Query(..., min_length=1), page:int = Query(1,ge=1), limit:int= Query(10,ge=1,le=50)):
    all_results = cached_search(q)
    total = len(all_results)

    # if not q.strip():
    #     return {"results": []}

    # all_results = run_search(q)

    # total = len(all_results)
    start = (page-1) *limit
    end = start + limit


    paginated = all_results[start:end]


    formatted = [
        {
            "title":result["title"],
            "url":result["url"],
            "score":result["score"],
            "snippet":result["snippet"]
        }
        for result in paginated
    ]

    return {"results":formatted,"total":total}