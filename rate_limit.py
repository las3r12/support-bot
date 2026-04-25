import time
import threading
from collections import deque


class IPRateLimiter:
    def __init__(self, max_requests: int, window_sec: int):
        self._max = max_requests
        self._window = window_sec
        self._buckets: dict[str, deque] = {}
        self._lock = threading.Lock()
        t = threading.Thread(target=self._cleanup_loop, daemon=True)
        t.start()

    def _cleanup_loop(self):
        while True:
            time.sleep(self._window)
            now = time.monotonic()
            with self._lock:
                stale = [ip for ip, bucket in self._buckets.items()
                         if not bucket or now - bucket[-1] > self._window]
                for ip in stale:
                    del self._buckets[ip]

    def is_allowed(self, ip: str) -> bool:
        now = time.monotonic()
        with self._lock:
            if ip not in self._buckets:
                self._buckets[ip] = deque()
            bucket = self._buckets[ip]
            while bucket and now - bucket[0] > self._window:
                bucket.popleft()
            if len(bucket) >= self._max:
                return False
            bucket.append(now)
            return True

    def next_allowed(self, ip: str) -> float:
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets.get(ip)
            if not bucket:
                return 0
            return round(self._window - (now - bucket[0]), 1)
