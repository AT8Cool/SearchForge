import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import random
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import deque

# --- SEEDS ---
seed_url = [
    "https://en.wikipedia.org/wiki/Computer_science",
    "https://medlineplus.gov/healthtopics.html",
    "https://www.geeksforgeeks.org/computer-networks/computer-network-tutorials/",
    "https://developer.mozilla.org/en-US/docs/Web/JavaScript",
    "https://en.wikipedia.org/wiki/Anime",
    "https://en.wikipedia.org/wiki/Valorant",
    "https://www.geeksforgeeks.org/python-programming-language/"
]

queue = deque(seed_url)
visited = set()
pages = []

MAX_PAGES = 1000
MAX_WORKERS = 15

allowed_domains = [
    "wikipedia.org",
    "geeksforgeeks.org",
    "developer.mozilla.org",
    "medlineplus.gov"
]

# --- HEADERS ---
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

# --- HELPERS ---
def detect_source(url):
    domain = urlparse(url).netloc
    if "wikipedia.org" in domain:
        return "wikipedia"
    elif "geeksforgeeks.org" in domain:
        return "gfg"
    elif "developer.mozilla.org" in domain:
        return "mdn"
    elif "medlineplus.gov" in domain:
        return "health"
    return "other"


def is_allowed(url):
    domain = urlparse(url).netloc
    
    #Wikipedia only for English
    if "wikipedia.org" in domain:
        return "en.wikipedia.org" in domain
    
    
    return any(d in domain for d in allowed_domains)


def is_valid_url(url):
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and "." in parsed.netloc
    except:
        return False


def parse_page(soup):
    title = soup.title.string if soup.title else ""

    # limit content (important)
    paragraphs = soup.find_all("p")[:10]
    text = " ".join(p.get_text() for p in paragraphs)

    return title, text


# --- FETCH ---
def fetch_page(url):
    try:
        # small delay per request (important)
        time.sleep(random.uniform(0.05, 0.1))

        response = requests.get(url, timeout=8, headers=headers)
        print(f"[{response.status_code}] {url}")

        if response.status_code != 200:
            return None

        return url, response.text

    except Exception as e:
        print(f"[ERROR] {url}")
        return None


# --- CRAWLER ---
def crawl():
    global queue, visited

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        while queue and len(visited) < MAX_PAGES:

            batch = []

            while queue and len(batch) < MAX_WORKERS * 2:
                url = queue.popleft()

                if url in visited or not is_allowed(url):
                    continue

                visited.add(url)
                batch.append(url)

            futures = [executor.submit(fetch_page, url) for url in batch]

            for future in as_completed(futures):
                result = future.result()
                if not result:
                    continue

                url, html = result
                soup = BeautifulSoup(html, "html.parser")

                title, text = parse_page(soup)

                pages.append({
                    "url": url,
                    "title": title,
                    "text": text,
                    "source": detect_source(url)
                })

                # --- LINK EXTRACTION ---
                for link in soup.find_all("a", href=True):
                    absolute_url = urljoin(url, link["href"])
                    absolute_url = absolute_url.split("#")[0]
                    absolute_url = absolute_url.split("?")[0]

                    # --- filters ---
                    if "(" in absolute_url or ")" in absolute_url:
                        continue

                    if not is_valid_url(absolute_url):
                        continue

                    if any(x in absolute_url for x in ["javascript:", "mailto:", "#"]):
                        continue
                    
                    if any(x in absolute_url for x in ["File:", "Category:", "Help:", "Special:", "Talk:"]):
                        continue

                    # --- domain filter ---
                    if not is_allowed(absolute_url):
                        continue

                    # --- dedup ---
                    if absolute_url in visited or absolute_url in queue:
                        continue

                    queue.append(absolute_url)


# --- RUN ---
crawl()

with open("data/pages.json", "w", encoding="utf-8") as f:
    json.dump(pages, f, ensure_ascii=False, indent=2)

print("Crawling complete.")