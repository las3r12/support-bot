from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import requests
from collections import deque

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def get_page(url):
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    return text

def crawl(start_url, max_depth=0):
    visited = set()
    results = []
    queue = deque([(start_url, 0)])
    domain = urlparse(start_url).netloc
    while queue:
        url, depth = queue.popleft()
        if url in visited or depth > max_depth:
            continue
        visited.add(url)
        try:
            resp = requests.get(url, timeout=5, headers=headers)
            if "text/html" not in resp.headers.get("Content-Type", ''):
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            results.append(soup.get_text(separator=" ", strip=True))

            if depth < max_depth:
                for tag in soup.find_all("a", href=True):
                    link = urljoin(url, tag['href'])
                    parsed = urlparse(link)
                    if parsed.netloc == domain and parsed.scheme in ("http", "https"):
                        if link not in visited:
                            queue.append((link, depth + 1))
        except Exception as e:
            print(f"Failed {url}: {e}")
            continue
    return results