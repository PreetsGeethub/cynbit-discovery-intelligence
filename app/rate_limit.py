import os
import threading
import time
from collections import deque

from fastapi import HTTPException, Request


class InMemoryRateLimiter:
    """Simple per-client sliding-window limiter for a single API process.

    For multiple workers/instances, replace this with a shared store such as Redis.
    """

    def __init__(self, limit: int = 5, window_seconds: int = 60):
        self.limit = max(1, int(os.getenv("ANALYZE_RATE_LIMIT_REQUESTS", limit)))
        self.window_seconds = max(
            1, int(os.getenv("ANALYZE_RATE_LIMIT_WINDOW_SECONDS", window_seconds))
        )
        self._requests: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def reset(self) -> None:
        """Clear counters; useful for deterministic tests."""
        with self._lock:
            self._requests.clear()

    def check(self, request: Request) -> None:
        client_host = request.client.host if request.client else "unknown"
        now = time.monotonic()
        cutoff = now - self.window_seconds

        with self._lock:
            timestamps = self._requests.setdefault(client_host, deque())
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()

            if len(timestamps) >= self.limit:
                retry_after = max(
                    1, int(self.window_seconds - (now - timestamps[0]))
                )
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded. Please retry later.",
                    headers={"Retry-After": str(retry_after)},
                )

            timestamps.append(now)


analyze_rate_limiter = InMemoryRateLimiter()
