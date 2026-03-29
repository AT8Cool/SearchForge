import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time

session = requests.Session()

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/"
}

seed =  "https://medlineplus.gov/healthtopics.html"

visited = set()
queue = [seed]

MAX_PAGES = 50


def fetch(url):
    try:
        res = session.get(url, headers=headers, timeout=10)
        print(f"{res.status_code} | {url}")
        if res.status_code != 200:
            return None
        return res.text
    except Exception as e:
        print("ERROR:", e)
        return None


def parse(html):
    soup = BeautifulSoup(html, "lxml")

    title = soup.title.string if soup.title else ""

    paragraphs = soup.find_all("p")
    text = " ".join(p.get_text() for p in paragraphs[:10])

    return title, text, soup


while queue and len(visited) < MAX_PAGES:
    url = queue.pop(0)

    if url in visited:
        continue

    visited.add(url)

    html = fetch(url)
    if not html:
        continue

    title, text, soup = parse(html)

    print("TITLE:", title[:60])

    for link in soup.find_all("a", href=True):
        href = link["href"]

        if href.startswith("https://medium.com"):
            if href not in visited and href not in queue:
                queue.append(href)

    # 🔴 IMPORTANT: slow down
    time.sleep(2)