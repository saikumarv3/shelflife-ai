"""FastAPI middleware — authentication, rate limiting, request logging."""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from config.settings import settings

logger = logging.getLogger(__name__)

OPEN_PATHS = {"/health", "/ready", "/docs", "/redoc", "/openapi.json", "/metrics"}


# ── API Key Authentication ───────────────────────────────────


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in OPEN_PATHS:
            return await call_next(request)

        api_key = request.headers.get("X-API-Key")
        if api_key != settings.api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key", "error_code": "UNAUTHORIZED"},
            )
        return await call_next(request)


# ── Rate Limiting (in-memory sliding window) ─────────────────


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in OPEN_PATHS:
            return await call_next(request)

        key = request.headers.get("X-API-Key", request.client.host if request.client else "unknown")
        now = time.time()
        cutoff = now - self.window

        self._requests[key] = [t for t in self._requests[key] if t > cutoff]
        remaining = self.max_requests - len(self._requests[key])

        if remaining <= 0:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded", "error_code": "RATE_LIMITED"},
                headers={
                    "Retry-After": str(self.window),
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                },
            )

        self._requests[key].append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining - 1)
        return response


# ── Request Logging ──────────────────────────────────────────


PREDICTION_PATHS = {"/predict/demand", "/predict/batch", "/predict/waste-risk", "/recommend"}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        from monitoring.metrics import PREDICTION_REQUESTS, PREDICTION_LATENCY

        request_id = str(uuid.uuid4())[:8]
        start = time.perf_counter()

        response = await call_next(request)

        latency_s = time.perf_counter() - start
        latency_ms = latency_s * 1000
        path = request.url.path

        if path in PREDICTION_PATHS:
            PREDICTION_REQUESTS.labels(endpoint=path, status=str(response.status_code)).inc()
            PREDICTION_LATENCY.labels(endpoint=path).observe(latency_s)

        log_data = {
            "request_id": f"req_{request_id}",
            "method": request.method,
            "path": path,
            "status_code": response.status_code,
            "latency_ms": round(latency_ms, 1),
            "client_ip": request.client.host if request.client else None,
        }
        logger.info(json.dumps(log_data))
        return response
