from collections import defaultdict, deque
from threading import Lock
import time


class UserLimiter:
    def __init__(self, max_concurrency=3, max_requests=60, window_seconds=60):
        self.max_concurrency = max_concurrency
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._active = defaultdict(int)
        self._requests = defaultdict(deque)
        self._lock = Lock()

    def acquire(self, uid):
        with self._lock:
            if self._active[uid] >= self.max_concurrency:
                return False
            now = time.monotonic()
            requests = self._requests[uid]
            while requests and now - requests[0] >= self.window_seconds:
                requests.popleft()
            if len(requests) >= self.max_requests:
                return False
            requests.append(now)
            self._active[uid] += 1
            return True

    def release(self, uid):
        with self._lock:
            if self._active[uid] > 0:
                self._active[uid] -= 1
