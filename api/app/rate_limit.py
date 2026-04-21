"""In-process sliding-window rate limiter for webhook endpoints.

Configurable via env vars:
  RATE_LIMIT_WEBHOOK        — max requests per window (default 60)
  RATE_LIMIT_WINDOW_SECONDS — window length in seconds (default 60)

These are per source IP. For multi-process deployments, swap the
in-memory store for a Redis-backed equivalent.
"""

import asyncio
import collections
import os
import time
from collections.abc import Callable
from typing import Any

from fastapi import Request, Response
from fastapi.responses import JSONResponse

_LIMIT = int(os.getenv("RATE_LIMIT_WEBHOOK", "60"))
_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
_CLEANUP_EVERY = 500  # sweep stale IP entries every N requests

# ip -> deque of request timestamps (float, monotonic)
_counters: dict[str, collections.deque] = {}
_lock = asyncio.Lock()
_request_count = 0


async def check_rate_limit(request: Request) -> Response | None:
    """Return a 429 Response if the caller has exceeded the rate limit, else None."""
    global _request_count
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    cutoff = now - _WINDOW

    async with _lock:
        _request_count += 1
        q = _counters.setdefault(ip, collections.deque())
        # Evict timestamps outside the current window
        while q and q[0] < cutoff:
            q.popleft()
        if len(q) >= _LIMIT:
            return JSONResponse(
                status_code=429,
                content={"error": "rate limit exceeded"},
                headers={"Retry-After": str(_WINDOW)},
            )
        q.append(now)
        # Periodically remove IPs with no recent requests to bound memory usage.
        if _request_count % _CLEANUP_EVERY == 0:
            stale = [k for k, v in _counters.items() if not v]
            for k in stale:
                del _counters[k]
    return None


def rate_limited(handler: Callable) -> Callable:
    """Decorator that applies per-IP rate limiting to a FastAPI route handler."""

    async def wrapper(request: Request, **kwargs: Any) -> Response:
        blocked = await check_rate_limit(request)
        if blocked is not None:
            return blocked
        return await handler(request, **kwargs)

    wrapper.__name__ = handler.__name__
    wrapper.__doc__ = handler.__doc__
    return wrapper
