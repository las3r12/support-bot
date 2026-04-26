from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import requests
from collections import deque
import threading
import ipaddress
import socket


class Scraper:
    def __init__(self, timeout=5):
        self.timeout = timeout
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
        if not self._is_safe_url(url):
            return None, []
        try:
            resp = requests.get(url, timeout=self.timeout, headers=self.headers)
            if "text/html" not in resp.headers.get("Content-Type", ''):
                return None, []
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            links = []
            if depth < max_depth:
                for tag in soup.find_all("a", href=True):
                    link = self._normalize(urljoin(url, tag['href']).split("#")[0])
                    parsed = urlparse(link)
                    if parsed.netloc == domain and parsed.scheme in ("http", "https"):
                        links.append(link)
            return soup.get_text(separator=" ", strip=True), links
        except Exception as e:
            print(f"Failed {url}: {e}")
            return None, []

    def _normalize(self, url: str) -> str:
        return url.rstrip("/")

    def get_links(self, start_url: str, max_links: int, max_depth: int = 0) -> list[str]:
        if not self._is_safe_url(start_url):
            raise ValueError(f"Blocked URL: {start_url}")
        start_url = self._normalize(start_url)
        visited = {start_url}
        links = [start_url]
        queue = deque([(start_url, 0)])
        domain = urlparse(start_url).netloc
        lock = threading.Lock()

        def worker(url, depth):
            _, found_links = self._fetch(url, depth, domain, max_depth)
            with lock:
                for link in found_links:
                    link = self._normalize(link)
                    if link not in visited and len(links) < max_links:
                        visited.add(link)
                        links.append(link)
                        queue.append((link, depth + 1))

        while queue and len(links) < max_links:
            batch = []
            while queue:
                batch.append(queue.popleft())
            threads = [threading.Thread(target=worker, args=(url, depth)) for url, depth in batch]
            for t in threads: t.start()
            for t in threads: t.join()

        return links[:max_links]

    def fetch_pages(self, urls: list[str]) -> str:
        results = []
        lock = threading.Lock()

        def worker(url):
            text, _ = self._fetch(url, 0, urlparse(url).netloc, 0)
            if text:
                with lock:
                    results.append(text)

        threads = [threading.Thread(target=worker, args=(url,)) for url in urls]
        for t in threads: t.start()
        for t in threads: t.join()
        return "\n\n".join(results)
    
    def _is_safe_url(self, url: str) -> bool:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        try:
            ip = ipaddress.ip_address(socket.getaddrinfo(hostname, None)[0][4][0])
        except Exception:
            return False
        return True
        return ip.is_global and not ip.is_loopback and not ip.is_private and not ip.is_link_local