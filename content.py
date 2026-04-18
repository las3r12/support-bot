from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import requests
from collections import deque
import threading

class Scarper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:149.0) Gecko/20100101 Firefox/149.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Priority": "u=0, i",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
        }

    def get_page(self, url):
        response = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        return text

    def _fetch(self, url, depth, domain, max_depth):
        try:
            resp = requests.get(url, timeout=5, headers=self.headers)
            if "text/html" not in resp.headers.get("Content-Type", ''):
                return None, []
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            links = []
            if depth < max_depth:
                for tag in soup.find_all("a", href=True):
                    link = urljoin(url, tag['href'])
                    parsed = urlparse(link)
                    if parsed.netloc == domain and parsed.scheme in ("http", "https"):
                        links.append(link)
            return soup.get_text(separator=" ", strip=True), links
        except Exception as e:
            print(f"Failed {url}: {e}")
            return None, []

    def crawl(self, start_url, max_depth=0):
        visited = set()
        results = []
        queue = deque([(start_url, 0)])
        domain = urlparse(start_url).netloc
        lock = threading.Lock()

        def worker(url, depth):
            text, links = self._fetch(url, depth, domain, max_depth)
            with lock:
                if text:
                    results.append(text)
                for link in links:
                    if link not in visited:
                        visited.add(link)
                        queue.append((link, depth + 1))

        while queue:
            batch = []
            while queue:
                url, depth = queue.popleft()
                if url not in visited and depth <= max_depth:
                    visited.add(url)
                    batch.append((url, depth))

            threads = [threading.Thread(target=worker, args=(url, depth)) for url, depth in batch]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        return results