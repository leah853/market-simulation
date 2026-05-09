"""Request-ID + access-log middleware.

Stamps every request with a UUID, binds it to structlog contextvars, exposes
it in the X-Request-Id response header, and emits an access-log line on every
response.
"""
from __future__ import annotations

import time
from uuid import uuid4

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger("hhah.access")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        rid = request.headers.get("X-Request-Id") or uuid4().hex
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=rid,
            method=request.method,
            path=request.url.path,
        )
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            logger.exception("request.failed", duration_ms=duration_ms)
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        response.headers["X-Request-Id"] = rid

        # Don't log noise on health checks
        if request.url.path != "/healthz":
            logger.info(
                "request.completed",
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
        return response
