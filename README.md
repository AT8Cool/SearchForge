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

## Project Flow

1. `crawler/crawler2.py` crawls allowed domains and writes `data/pages.jsonl`
2. `indexer/build_index.py` builds `data/index.json` and `data/idf.json`
3. `app/models/json_to_sqlite.py` loads the corpus and index into `data/search.db`
4. `app/core/pagerank.py` computes PageRank scores from the stored link graph
5. `app/main.py` serves search results through FastAPI


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
## Notes

- The current public demo uses a curated, frozen dataset for stability
- Ranking is tuned for demo quality, not full web-scale search
- `data/` is ignored by git, so search data may need to be generated locally
- The frontend began from a UI starter and was adapted into the current public demo
- The UI uses components from `shadcn/ui` under the MIT license

## Author

- GitHub: `https://github.com/AT8Cool`
- LinkedIn: `https://www.linkedin.com/in/atharva-bhosale-ab9659302/`
