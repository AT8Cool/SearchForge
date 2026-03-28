import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import random
import time
import json

seed_url = "https://en.wikipedia.org/wiki/Computer_science"
queue = [seed_url] 
visited = set()
max_page = 300
allowed_domains = [
    "wikipedia.org",
    "geeksforgeeks.org",
    "stackoverflow.com"
]

def is_allowed(url):
    domain = urlparse(url).netloc
    return any(d in domain for d in allowed_domains)


headers = {"User-Agent": "Mozilla/5.0 (compatible; MyCrawler/1.0)"}
# response = requests.get(seed_url, headers=headers)
# print(response)    

# --- PARSERS ---
def parse_page(url, soup):
    domain = urlparse(url).netloc

    title = soup.title.string if soup.title else ""
    # Wikipedia
    if "wikipedia.org" in domain:
        paragraphs = soup.find_all("p")
        text = " ".join(p.get_text() for p in paragraphs)

    return title, text

pages = []

def crawl():
 
    while queue and len(visited) < max_page:
        
        url = queue.pop(0)

        if url in visited:
            continue

        if not is_allowed(url):
            continue

        try:
            response = requests.get(url, timeout=5, headers=headers)
            print(f"Visiting: {url} | Status Code: {response.status_code}")
        except Exception as e:
            print(f"Failed: {url} | Error: {e}")
            continue

        visited.add(url)  

        soup = BeautifulSoup(response.text, "html.parser")
         
        # title = soup.title.string if soup.title else ""
        # paragraphs = soup.find_all("p")
        # text = " ".join(p.get_text() for p in paragraphs)
        
        title, text = parse_page(url,soup)
        pages.append({
            "url":url,
            "title":title,
            "text":text

        })
        
        for link in soup.find_all("a", href=True):  
            absolute_url = urljoin(url, link["href"])
            
            if urlparse(absolute_url).netloc == urlparse(seed_url).netloc:
                
                    if absolute_url not in visited and absolute_url not in queue:
                                queue.append(absolute_url)

        time.sleep(random.uniform(1,2))

crawl()
with open("data/pages.json","w",encoding="utf-8") as f:
    json.dump(pages,f,ensure_ascii=False,indent=2)

print("Crawling complete. Data saved to pages.json")