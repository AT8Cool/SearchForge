# Vichar Search Engine

Vichar is a focused search engine prototype that crawls, indexes, and ranks web content through a FastAPI backend and a modern React interface. The project was built as an end-to-end information retrieval system, with the goal of understanding how ranking quality improves when crawling, indexing, and scoring are iterated together instead of treated as separate pieces.

## The Journey

This project did not start in its current form.

The earliest version began with a simpler TF-IDF-style ranking approach on a smaller crawl. That version helped establish the basics: tokenization, inverted indexing, stop-word filtering, and query matching. It worked, but the ranking quality was uneven, especially when document lengths varied too much or exact term frequency dominated the result order.

From there, the ranking system moved to BM25. That shift made the search feel much more grounded because BM25 handled document-length normalization more naturally and produced stronger lexical ranking behavior for real search queries. Once the core retrieval quality improved, PageRank was added on top of the crawled link graph to introduce authority signals and make the search engine feel more like a true retrieval system rather than a plain keyword matcher.

The crawler also went through three iterations before settling on the current version:

1. `crawler/crawler.py`
   A basic threaded crawler that proved the pipeline end to end.
2. `crawler/crawler1.py`
   A larger and more ambitious crawl attempt with broader domain coverage and batch writing.
3. `crawler/crawler2.py`
   The final async crawler, with domain-aware throttling, retries, buffered writes, and a structure better suited for larger controlled crawls.

That progression shaped the final system: better crawling produced cleaner data, cleaner data improved indexing, and better indexing made the ranking changes from TF-IDF to BM25 to PageRank much more meaningful.

## What It Includes

- An async crawler that collects pages into `data/pages.jsonl`
- An indexer that builds an inverted index and IDF data
- A SQLite loading step for fast local search
- A PageRank stage based on the crawled link graph
- A FastAPI backend with `/search`
- A React frontend for public demo use

## Ranking Evolution

- Started with a TF-IDF-style ranking approach
- Moved to BM25 for stronger lexical relevance and length normalization
- Added PageRank to introduce authority from the internal link graph
- Applied source weighting, title boosts, URL normalization, and snippet generation for better result quality

## Demo Highlights

The current demo is built around a curated, cleaned dataset and performs well on queries such as:

- `What is Database`
- `NASA Moon Mission`
- `Computer Science`
- `Theory of Computation`
- `Python`

## Screenshots

The current demo includes these views:

- Home page with guided starter suggestions
- Search results for database-oriented queries
- Search results for NASA and Artemis mission coverage
- Search results for theory of computation
- About page with project and profile links

Note:
The screenshots shared during development are not embedded here yet because they are not stored as image files inside the repository. Once they are added to the repo as local assets, they can be linked here directly.

## Tech Stack

- Python
- FastAPI
- SQLite
- aiohttp
- BeautifulSoup
- React
- Vite

## Hosting

The cleanest public setup for this project is:

- Frontend on Vercel
- Backend on Render

### Why split it this way

- Vercel handles the React frontend well and works nicely with a subdirectory project
- Render is a simple fit for the FastAPI backend
- The frontend now reads its backend URL from `VITE_API_BASE_URL` instead of hardcoding localhost
- The backend now supports `SEARCH_DB_PATH`, a `/api/search` route, and a `/api/health` route for deployment

### Backend on Render

The repo now includes:

- `render.yaml`
- `requirements.deploy.txt`
- `scripts/ensure_search_db.py`

Render will build the API with:

```text
pip install -r requirements.deploy.txt
```

and start it with:

```text
python scripts/ensure_search_db.py && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

You have two practical ways to supply the SQLite database:

1. Fastest path:
   Force-add `data/search.db` to git for the demo deploy.
2. Cleaner path:
   Upload `search.db` somewhere public, then set `SEARCH_DB_URL` in Render so the backend downloads it on boot.

The current `search.db` is roughly 86 MB, so the fast path is workable for a demo repo but still heavier than ideal.

Recommended environment variables:

```text
SEARCH_DB_PATH=data/search.db
SEARCH_DB_URL=<public-url-to-search.db>
```

### Frontend on Vercel

The frontend folder is:

```text
app/templates/Vichar Search Engine Homepage
```

Set that folder as the Vercel project root.

The repo now includes:

- `.env.example`
- `vercel.json`

Set this environment variable in Vercel:

```text
VITE_API_BASE_URL=https://your-render-backend.onrender.com
```

`vercel.json` rewrites all routes to `index.html`, which keeps the React Router paths working for `/`, `/search`, and `/about`.

### Deployment Notes

- Render Free services spin down after inactivity, so the first request can be slow
- Render Free services use an ephemeral filesystem, so a database downloaded from `SEARCH_DB_URL` must be downloaded again after a cold restart
- If you want a smoother public demo, a paid Render instance with persistent storage is the more stable option
- The frontend and backend can still be run locally without any deployment-only changes

## Project Flow

1. `crawler/crawler2.py` crawls allowed domains and writes `data/pages.jsonl`
2. `indexer/build_index.py` builds `data/index.json` and `data/idf.json`
3. `app/models/json_to_sqlite.py` loads the corpus and index into `data/search.db`
4. `app/core/pagerank.py` computes PageRank scores from the stored link graph
5. `app/main.py` serves search results through FastAPI

## Main Files

```text
Search-engine/
|-- crawler/
|   |-- crawler.py
|   |-- crawler1.py
|   `-- crawler2.py
|-- indexer/
|   `-- build_index.py
|-- app/
|   |-- main.py
|   |-- core/
|   |   |-- search.py
|   |   `-- pagerank.py
|   `-- models/
|       |-- create_db.py
|       `-- json_to_sqlite.py
|-- data/
|-- pipeline.py
`-- README.md
```

## Local Setup

### Backend

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Build the Search Data

Run the full pipeline:

```powershell
python pipeline.py
```

Useful pipeline flags:

```powershell
python pipeline.py --skip-clean --skip-crawl
python pipeline.py --max-pages 5000 --crawler-workers 100
```

### Start the API

```powershell
uvicorn app.main:app --reload
```

Backend URL:

```text
http://127.0.0.1:8000
```

### Frontend

```powershell
cd "app/templates/Vichar Search Engine Homepage"
npm install
npm run dev
```

Frontend URL:

```text
http://127.0.0.1:5173
```

## Search API

Endpoint:

```text
GET /api/search?q=<query>&page=1&limit=10
```

Example:

```text
http://127.0.0.1:8000/api/search?q=computer%20science&page=1&limit=10
```

Response shape:

```json
{
  "results": [
    {
      "title": "Computer science - Wikipedia",
      "url": "https://en.wikipedia.org/wiki/Computer_science",
      "score": 123.45,
      "snippet": "Computer science is the study of computation..."
    }
  ],
  "total": 1
}
```

## Notes

- The current public demo uses a curated, frozen dataset for stability
- Ranking is tuned for demo quality, not full web-scale search
- `data/` is ignored by git, so search data may need to be generated locally
- The frontend began from a UI starter and was adapted into the current public demo
- The UI uses components from `shadcn/ui` under the MIT license

## Author

- GitHub: `https://github.com/AT8Cool`
- LinkedIn: `https://www.linkedin.com/in/atharva-bhosale-ab9659302/`
