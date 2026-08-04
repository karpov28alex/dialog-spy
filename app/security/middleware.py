from __future__ import annotations

from collections.abc import Awaitable, Callable
from time import time

import structlog
from redis.asyncio import Redis
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from app.core.config import get_settings

logger = structlog.get_logger()

RATE_LIMITED_ROUTES = {
    ("POST", "/api/auth/telegram"): (20, 60),
    ("POST", "/api/admin/auth/login"): (10, 300),
}
MAX_REQUEST_BODY_BYTES = 2 * 1024 * 1024


class SecurityMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.settings = get_settings()

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        response = await self._reject_oversized_request(request)
        if response is None:
            response = await self._enforce_rate_limit(request)
        if response is not None:
            await response(scope, receive, send)
            return

        async def send_with_security_headers(message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(
                    [
                        (b"x-content-type-options", b"nosniff"),
                        (b"x-frame-options", b"DENY"),
                        (b"referrer-policy", b"no-referrer"),
                        (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
                    ]
                )
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_security_headers)

    async def _reject_oversized_request(self, request: Request) -> Response | None:
        raw_length = request.headers.get("content-length")
        if raw_length is None:
            return None
        try:
            content_length = int(raw_length)
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length"})
        if content_length <= MAX_REQUEST_BODY_BYTES:
            return None
        return JSONResponse(status_code=413, content={"detail": "Request body too large"})

    async def _enforce_rate_limit(self, request: Request) -> Response | None:
        policy = RATE_LIMITED_ROUTES.get((request.method, request.url.path))
        if policy is None:
            return None

        limit, window_seconds = policy
        identity = _client_identity(request)
        window = int(time()) // window_seconds
        key = f"dialog_spy:rate_limit:{request.method}:{request.url.path}:{identity}:{window}"
        redis = Redis.from_url(self.settings.redis_url, decode_responses=True)
        try:
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, window_seconds + 1)
        except Exception:
            logger.exception("rate_limit_backend_unavailable", route=request.url.path)
            return None
        finally:
            await redis.aclose()

        if count <= limit:
            return None
        retry_after = window_seconds - (int(time()) % window_seconds)
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests"},
            headers={"Retry-After": str(max(retry_after, 1))},
        )


def _client_identity(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"
