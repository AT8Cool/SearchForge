# Search Engine

A small search engine project built with Python, FastAPI, and a React/Vite UI. It crawls a slice of Wikipedia, builds an inverted index, ranks documents with a BM25-style scoring flow, and exposes the results through a simple `/search` API.

The project is split into three main stages:

1. `crawler/` collects pages and stores them in `data/pages.json`
2. `indexer/` builds `data/index.json` and `data/idf.json`
3. `app/` serves ranked search results through FastAPI

## Features

- Crawl pages starting from a Wikipedia seed URL
- Build an inverted index from crawled page text
- Score results with BM25-style ranking plus title/query boosts
- Generate snippets from the best matching sentence
- Expose paginated results with FastAPI
- Optional React frontend in `app/templates/Vichar Search Engine Homepage`

## Project Structure

```text
Search-engine/
|-- crawler/
|   |-- crawler.py
|   `-- parser.py
|-- indexer/
|   `-- build_index.py
|-- app/
|   |-- main.py
|   |-- search.py
|   `-- templates/
|       `-- Vichar Search Engine Homepage/
|-- data/
|-- requirements.txt
`-- README.md
```

## How It Works

### 1. Crawl

`crawler/crawler.py` starts from:

```text
https://en.wikipedia.org/wiki/Computer_science
```

It visits up to `200` pages, extracts the page title plus paragraph text, and saves the dataset to `data/pages.json`.

### 2. Build the Index

`indexer/build_index.py`:

- tokenizes page text with NLTK
- removes stop words
- counts term frequency per document
- builds an inverted index
- computes IDF values

The generated files are:

- `data/index.json`
- `data/idf.json`

### 3. Search

`app/search.py` loads the generated data and:

- tokenizes the query
- removes stop words when possible
- computes BM25-style scores
- boosts exact and partial title matches
- deduplicates normalized URLs
- returns a title, URL, score, and snippet for each result

### 4. API

`app/main.py` exposes:

- `GET /`
- `GET /search?q=<query>&page=1&limit=10`

Example:

```text
http://127.0.0.1:8000/search?q=computer%20science&page=1&limit=10
```

Response shape:

```json
{
  "results": [
    {
      "title": "Example title",
      "url": "https://example.com/page",
      "score": 123.45,
      "snippet": "Short matching text..."
    }
  ],
  "total": 1
}
```

## Local Setup

### 1. Create and activate a virtual environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. Install Python dependencies

```powershell
pip install -r requirements.txt
```

### 3. Download required NLTK data

```powershell
python -c "import nltk; nltk.download('stopwords'); nltk.download('punkt'); nltk.download('punkt_tab')"
```

### 4. Generate crawl data and index files

Skip this if `data/pages.json`, `data/index.json`, and `data/idf.json` already exist locally.

```powershell
python crawler/crawler.py
python indexer/build_index.py
```

### 5. Start the API

```powershell
uvicorn app.main:app --reload
```

The backend will be available at:

```text
http://127.0.0.1:8000
```

## Frontend

A React/Vite frontend is included here:

```text
app/templates/Vichar Search Engine Homepage
```

To run it:

```powershell
cd "app/templates/Vichar Search Engine Homepage"
npm install
npm run dev
```

The frontend fetches results from:

```text
http://127.0.0.1:8000/search
```

So the FastAPI backend should be running at the same time.

## Notes

- `data/` is listed in `.gitignore`, so another developer may need to regenerate the crawl and index files locally.
- The crawler is currently limited to the same domain as the seed URL and capped at `200` pages.
- The seed URL is hard-coded in `crawler/crawler.py`.
- `crawler/parser.py` is currently empty and appears to be reserved for future parsing logic.
- Ranking is tuned for this small dataset, not for a production-scale web search engine.

## Possible Next Improvements

- Make the seed URL and crawl limit configurable
- Store crawl data in a database instead of JSON files
- Add tests for indexing and ranking behavior
- Expand the crawler beyond a single domain
- Improve relevance tuning and snippet generation
