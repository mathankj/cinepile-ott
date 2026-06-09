"""
In-process sliding-window rate limiter, applied as a FastAPI dependency.

Scope: brute-force defence on the unauthenticated auth endpoints (login,
signup). Keyed by client IP.

IMPORTANT — this limiter is PER PROCESS. State lives in this module, so each
gunicorn/uvicorn worker counts independently. That is fine at workers=1 (our
current deployment); when we scale out horizontally, replace the backing store
with Redis (INCR + EXPIRE or a sorted set) and keep this same dependency API.

Why a dependency and not middleware: only a couple of routes need limiting,
the limits differ per route, and a dependency keeps the policy visible right
next to the route definition.
"""
from __future__ import annotations

import math
import time
from collections import defaultdict, deque
from typing import Any

from fastapi import Depends, HTTPException, Request, status

from app.core.config import get_settings


class SlidingWindowLimiter:
    """Tracks recent hit timestamps per key and rejects when a window fills.

    No locking needed: FastAPI dependencies for a single process run on one
    event loop, and this code never awaits between read and write.
    """

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def hit(self, key: str, *, limit: int, window_seconds: float) -> float | None:
        """Record a hit. Returns None if allowed, or seconds-until-allowed
        (for the Retry-After header) if the key is over its limit."""
        now = time.monotonic()
        timestamps = self._hits[key]

        # Drop hits that have slid out of the window.
        cutoff = now - window_seconds
        while timestamps and timestamps[0] <= cutoff:
            timestamps.popleft()

        if len(timestamps) >= limit:
            # The oldest remaining hit is the one that has to expire before
            # another request fits in the window.
            return window_seconds - (now - timestamps[0])

        timestamps.append(now)
        return None

    def reset(self) -> None:
        """Test hook — wipe all counters."""
        self._hits.clear()


# Module-level singleton: all routes share one limiter (keys are namespaced
# per route by the `scope` argument below).
limiter = SlidingWindowLimiter()


def client_ip(request: Request) -> str:
    """Best-effort client IP. Behind our nginx/Render proxy the real client is
    the first entry of X-Forwarded-For; direct connections fall back to the
    socket peer address."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    return request.client.host if request.client else "unknown"


def rate_limit(scope: str, *, limit: int, window_seconds: int = 60) -> Any:
    """Build a route dependency enforcing `limit` requests per `window_seconds`
    per client IP. Usage:

        @router.post("/login", dependencies=[rate_limit("login", limit=10)])
    """

    async def _check(request: Request) -> None:
        if not get_settings().rate_limit_enabled:
            return

        retry_after = limiter.hit(
            f"{scope}:{client_ip(request)}", limit=limit, window_seconds=window_seconds
        )
        if retry_after is not None:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": {
                        "code": "rate_limited",
                        "message": "Too many requests. Please try again shortly.",
                    }
                },
                headers={"Retry-After": str(max(1, math.ceil(retry_after)))},
            )

    return Depends(_check)
