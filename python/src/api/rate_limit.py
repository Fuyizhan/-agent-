"""基于 IP 的内存滑动窗口限流。"""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ..config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/api/v1/health":
            return await call_next(request)
        ip = self._client_ip(request)
        now = time.time()
        self._requests[ip] = [value for value in self._requests[ip] if value > now - self.window_seconds]
        self._requests[ip].append(now)
        if len(self._requests[ip]) > self.max_requests:
            retry_after = max(int(self.window_seconds - (now - self._requests[ip][0])), 1)
            return JSONResponse(
                status_code=429,
                content={"detail": "请求过于频繁，请稍后重试", "error_code": "RATE_LIMITED"},
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)


def register_rate_limit(app: FastAPI) -> None:
    app.add_middleware(
        RateLimitMiddleware,
        max_requests=settings.RATE_LIMIT_PER_MINUTE,
        window_seconds=60,
    )
