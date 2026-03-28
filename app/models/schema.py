from pydantic import BaseModel

class SearchResponse(BaseModel):
    title: str
    url:str
    snippet: str
    score: str
    