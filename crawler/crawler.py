import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import random
import time
import json

seed_url = "https://en.wikipedia.org/wiki/The_Girl_I_Like_Forgot_Her_Glasses"



queue = [seed_url]
visited = set()
max_page = 100

headers = {"User-Agent": "Mozilla/5.0 (compatible; MyCrawler/1.0)"}
# response = requests.get(seed_url, headers=headers)
# print(response)    

pages = []

def crawl():
 
    while queue and len(visited) < max_page:
        
        url = queue.pop(0)

        if url in visited:
            continue

        try:
            response = requests.get(url, timeout=5, headers=headers)
            print(f"Visiting: {url} | Status Code: {response.status_code}")
        except Exception as e:
            print(f"Failed: {url} | Error: {e}")
            continue

        visited.add(url)  

        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.string if soup.title else ""
        text = soup.get_text()

        pages.append({
            "url":url,
            "title":title,
            "text":text

        })
        
        for link in soup.find_all("a", href=True):  
            absolute_url = urljoin(url, link["href"])
            # if urlparse(absolute_url).netloc == urlparse(seed_url).netloc:
            # if absolute_url not in visited:
            queue.append(absolute_url)

        time.sleep(random.uniform(1,2))

crawl()
with open("pages.json","w",encoding="utf-8") as f:
    json.dump(pages,f,ensure_ascii=False,indent=2)

print("Crawling complete. Data saved to pages.json")