import time
from typing import Dict, List
from fastapi import Request, HTTPException, status
from backend.app.core.config import settings

class SimpleRateLimiter:
    """
    In-memory sliding window rate limiter per client IP.
    """
    def __init__(self, requests_per_minute: int = 120):
        self.limit = requests_per_minute
        self.requests: Dict[str, List[float]] = {}

    def check_rate_limit(self, request: Request):
        client_ip = request.client.host if request.client else "127.0.0.1"
        now = time.time()
        window_start = now - 60.0

        timestamps = self.requests.setdefault(client_ip, [])
        # Prune old timestamps
        self.requests[client_ip] = [t for t in timestamps if t > window_start]

        if len(self.requests[client_ip]) >= self.limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: maximum {self.limit} requests per minute."
            )

        self.requests[client_ip].append(now)

rate_limiter = SimpleRateLimiter(settings.RATE_LIMIT_PER_MINUTE)
