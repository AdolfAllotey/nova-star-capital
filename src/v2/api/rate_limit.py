"""
Minimal rate limit helper.
If you don't use it yet, it stays harmless and import-safe.
"""

from __future__ import annotations
import time
from collections import defaultdict, deque
from typing import Deque, DefaultDict


class SimpleRateLimiter:
    """
    In-memory sliding-window limiter: max_calls per window_seconds per key.
    """
    def __init__(self, max_calls: int = 60, window_seconds: int = 60):
        self.max_calls = int(max_calls)
        self.window_seconds = int(window_seconds)
        self._calls: DefaultDict[str, Deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.time()
        q = self._calls[key]
        # purge old
        cutoff = now - self.window_seconds
        while q and q[0] < cutoff:
            q.popleft()
        if len(q) >= self.max_calls:
            return False
        q.append(now)
        return True
