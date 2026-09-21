"""M2.11: Token bucket 限速器。
替换固定 sleep；与并发窗口配合。
"""
from __future__ import annotations

import threading
import time


class TokenBucket:
    def __init__(self, rate_per_sec: float, capacity: float = None):
        """rate_per_sec: 每秒允许请求数；capacity: 桶容量（默认=rate）。"""
        self.rate = rate_per_sec
        self.capacity = capacity or max(rate_per_sec, 1.0)
        self.tokens = self.capacity
        self.last = time.monotonic()
        self.lock = threading.Lock()

    def acquire(self, cost: float = 1.0):
        """阻塞直到拿到 token。"""
        while True:
            with self.lock:
                now = time.monotonic()
                elapsed = now - self.last
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
                self.last = now
                if self.tokens >= cost:
                    self.tokens -= cost
                    return
                wait = (cost - self.tokens) / self.rate
            time.sleep(wait)
