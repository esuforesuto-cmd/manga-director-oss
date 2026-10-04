"""Fixed-window in-memory rate limiter boundary and implementation."""

from __future__ import annotations

from collections import defaultdict, deque
from time import monotonic
from typing import Protocol


class RateLimiter(Protocol):
    """Decide whether one request can proceed for a key."""

    def allow(self, key: str) -> bool:
        """Return whether the key is inside its configured limit."""


class MemoryRateLimiter:
    """Simple process-local sliding time-window limiter."""

    def __init__(self, limit: int = 60, window_seconds: float = 60) -> None:
        self.limit = limit
        self.window = window_seconds
        self._requests: defaultdict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = monotonic()
        requests = self._requests[key]
        while requests and requests[0] <= now - self.window:
            requests.popleft()
        if len(requests) >= self.limit:
            return False
        requests.append(now)
        return True
