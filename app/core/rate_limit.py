"""Small single-process rate limiter shared by public endpoints."""
from collections import defaultdict, deque
from time import monotonic

from fastapi import HTTPException, Request

_attempts: dict[tuple[str, str], deque[float]] = defaultdict(deque)
_windows: dict[str, int] = {}


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def enforce_rate_limit(key: str, *, scope: str, limit: int, window_seconds: int, message: str) -> None:
    now = monotonic()
    _windows[scope] = window_seconds
    for bucket_key, timestamps in list(_attempts.items()):
        cutoff = now - _windows.get(bucket_key[0], window_seconds)
        while timestamps and timestamps[0] <= cutoff:
            timestamps.popleft()
        if not timestamps:
            _attempts.pop(bucket_key, None)
    bucket = _attempts[(scope, key)]
    if len(bucket) >= limit:
        raise HTTPException(status_code=429, detail=message)
    bucket.append(now)
