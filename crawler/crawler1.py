import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
import random
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import deque
import os

# ================= CONFIG =================
MAX_PAGES = 20000
MAX_WORKERS = 50
MAX_PER_DOMAIN = 300
BATCH_SIZE = 1000

OUTPUT_FILE = "pages.jsonl"
FAILED_LOG = "failed_urls.log"

# ================= SEEDS =================
seed_url = [
    # --- CORE KNOWLEDGE ---
    "https://en.wikipedia.org/wiki/Computer_science",
    "https://en.wikipedia.org/wiki/Mathematics",
    "https://en.wikipedia.org/wiki/Database",
    "https://en.wikipedia.org/wiki/Artificial_intelligence",
    "https://en.wikipedia.org/wiki/Computer_Network",
    "https://en.wikipedia.org/wiki/Operating_system",
    "https://en.wikipedia.org/wiki/Programming_language",
    "https://en.wikipedia.org/wiki/Theory_of_computation",
    "https://en.wikipedia.org/wiki/Programming_paradigm",
    "https://en.wikipedia.org/wiki/Data_structure",
    "https://en.wikipedia.org/wiki/",


    # --- HEALTH ---
    "https://medlineplus.gov/healthtopics.html",

    # --- SCIENCE ---
    "https://www.nasa.gov/",

    # --- PROGRAMMING DOCS ---
    "https://developer.mozilla.org/en-US/docs/Web",

    # --- EDUCATION ---
    "https://cs50.harvard.edu/x/",

    # --- GENERAL KNOWLEDGE ---
    "https://www.britannica.com/",

    # --- TECH NEWS ---
    "https://www.theverge.com/tech",

    # --- FINANCE ---
    "https://www.investopedia.com/",

    # --- Q&A / DEV ---
    "https://stackoverflow.com/questions"
]
# ================= STATE =================
queue = deque(seed_url)
visited = set()
domain_count = {}

# ================= STATS =================
stats = {
    "scheduled": 0,
    "success": 0,
    "failed": 0,
    "skipped": 0,
    "http_error": 0,
    "timeout": 0,
    "parse_fail": 0,
    "retries": 0
}

# ================= SESSION =================
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0"
})

# ================= FILTERS =================
allowed_domains = [
    # --- CORE ---
    "wikipedia.org",

    # --- PROGRAMMING DOCS ---
    "developer.mozilla.org",
    "docs.python.org",
    "nodejs.org",
    "rust-lang.org",
    "nextjs.org",
    "react.dev",

    # --- PROGRAMMING LEARNING ---
    "freecodecamp.org",
    "w3schools.com",
    "geeksforgeeks.org",
    "programiz.com",
    "tutorialspoint.com",

    # --- COURSES ---
    "cs50.harvard.edu",
    "khanacademy.org",

    # --- SCIENCE ---
    "nationalgeographic.com",
    "sciencedaily.com",
    "livescience.com",
    "britannica.com",
    "nasa.gov",
    "esa.int",
    "scientificamerican.com",
    "ocw.mit.edu",

    # --- HEALTH ---
    "medlineplus.gov",
    "cdc.gov",
    "who.int",
    "genome.gov",
    "ncbi.nlm.nih.gov",
    "nature.com",
    "science.org",

    # --- EDUCATION ---
    "openstax.org",
    "ck12.org",
    "pll.harvard.edu",

    # --- NEW (IMPORTANT) ---
    "theverge.com",
    "investopedia.com",
    "stackoverflow.com",
]

allowed_domains += [
    "myanimelist.net",
    "animenewsnetwork.com",
    "ign.com",
    "gamespot.com"
]



bad_patterns = [
    "privacy", "terms", "login", "signup",
    "account", "policy", "cdn-cgi",
    "profile", "comment", "tag", "author",
    "video", "gallery"
]
bad_patterns += [
    # --- NEW CLEANUP ---
    "share", "print", "download",
    "login", "signup", "register",
    "advert", "ads",
    "?utm_", "&utm_"
]

bad_patterns += [
    "episode", "season", "watch",
    "review", "trailer", "gallery",
    "characters", "cast", "staff",
    "forum", "user", "profile",
    "tag", "topic", "news"
]

# ================= HELPERS =================
def canonicalize(url):
    parsed = urlparse(url)
    return urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower().replace("www.", ""),
        parsed.path.rstrip("/"),
        "", "", ""
    ))

def is_allowed(url):
    domain = urlparse(url).netloc
    if "wikipedia.org" in domain:
        return "en.wikipedia.org" in domain
    return any(domain.endswith(d) for d in allowed_domains)

def is_valid(url):
    try:
        p = urlparse(url)
        return p.scheme in ("http", "https") and "." in p.netloc
    except:
        return False

def detect_source(url):
    d = urlparse(url).netloc

    if "wikipedia" in d: return "wikipedia"
    if "developer.mozilla" in d: return "mdn"
    if "docs.python" in d: return "docs"
    if "stackoverflow" in d: return "qa"
    if "investopedia" in d: return "finance"
    if "theverge" in d: return "news"
    if "nasa" in d: return "science"
    if "medlineplus" in d: return "health"
    if "britannica" in d: return "encyclopedia"

    return "other"

def parse_page(soup):
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    paragraphs = soup.find_all("p")[:10]
    text = " ".join(p.get_text().strip() for p in paragraphs)

    if len(text) < 100:
        return None, None

    return title, text

# ================= FETCH WITH RETRY =================
def fetch(url, retry=False):
    try:
        time.sleep(random.uniform(0.05, 0.2))
        r = session.get(url, timeout=6)

        if r.status_code != 200:
            stats["http_error"] += 1
            if not retry:
                stats["retries"] += 1
                return fetch(url, retry=True)
            stats["failed"] += 1
            with open(FAILED_LOG, "a") as f:
                f.write(url + "\n")
            return None

        # content-type filter
        if "text/html" not in r.headers.get("Content-Type", ""):
            stats["failed"] += 1
            return None

        return url, r.text

    except requests.exceptions.Timeout:
        stats["timeout"] += 1
        if not retry:
            stats["retries"] += 1
            return fetch(url, retry=True)
        stats["failed"] += 1
        with open(FAILED_LOG, "a") as f:
            f.write(url + "\n")
        return None

    except:
        if not retry:
            stats["retries"] += 1
            return fetch(url, retry=True)
        stats["failed"] += 1
        with open(FAILED_LOG, "a") as f:
            f.write(url + "\n")
        return None

def write_batch(batch):
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        for item in batch:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

# ================= CRAWLER =================
def crawl():
    buffer = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:

        while queue and len(visited) < MAX_PAGES:

            batch_urls = []

            while queue and len(batch_urls) < MAX_WORKERS:
                url = canonicalize(queue.popleft())

                if url in visited or not is_allowed(url):
                    continue

                domain = urlparse(url).netloc

                if domain_count.get(domain, 0) >= MAX_PER_DOMAIN:
                    continue

                domain_count[domain] = domain_count.get(domain, 0) + 1
                visited.add(url)
                stats["scheduled"] += 1
                batch_urls.append(url)

            futures = [executor.submit(fetch, u) for u in batch_urls]

            for f in as_completed(futures):
                result = f.result()
                if not result:
                    continue

                url, html = result

                # ---- SAFE PARSER ----
                try:
                    soup = BeautifulSoup(html, "html.parser")
                except:
                    stats["parse_fail"] += 1
                    stats["failed"] += 1
                    continue

                title, text = parse_page(soup)
                if not title or not text:
                    stats["parse_fail"] += 1
                    stats["skipped"] += 1
                    continue

                links = []

                for tag in soup.find_all("a", href=True):
                    href = tag["href"]

                    if any(x in href for x in ["javascript:", "mailto:", "#"]):
                        continue

                    abs_url = canonicalize(urljoin(url, href))

                    if any(x in abs_url for x in ["myanimelist", "ign", "gamespot"]):
                        if abs_url.count("/") > 5:
                            continue

                    if not is_valid(abs_url):
                        continue

                    if any(p in abs_url for p in bad_patterns):
                        continue

                    if not is_allowed(abs_url):
                        continue

                    if abs_url not in visited:
                        queue.append(abs_url)
                        links.append(abs_url)

                    if len(links) >= 25:
                        break

                buffer.append({
                    "url": url,
                    "title": title,
                    "text": text,
                    "source": detect_source(url),
                    "links": links
                })

                stats["success"] += 1

                if len(buffer) >= BATCH_SIZE:
                    write_batch(buffer)
                    buffer.clear()

                print(f"[{stats['scheduled']}] DONE {url}")

    if buffer:
        write_batch(buffer)

# ================= RUN =================
if __name__ == "__main__":
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)

    if os.path.exists(FAILED_LOG):
        os.remove(FAILED_LOG)

    crawl()

    print("\n==== CRAWL STATS ====")
    print(f"Scheduled: {stats['scheduled']}")
    print(f"Success:   {stats['success']}")
    print(f"Failed:    {stats['failed']}")
    print(f"Skipped:   {stats['skipped']}")
    print(f"HTTP Err:  {stats['http_error']}")
    print(f"Timeouts:  {stats['timeout']}")
    print(f"ParseFail: {stats['parse_fail']}")
    print(f"Retries:   {stats['retries']}")