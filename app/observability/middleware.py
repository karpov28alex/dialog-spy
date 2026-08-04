from __future__ import annotations

from time import perf_counter, time

import structlog
from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import get_settings
from app.observability.metrics import runtime_metrics

logger = structlog.get_logger()
settings = get_settings()

RATE_LIMITED_ROUTES = {
    ("POST", "/api/auth/telegram"): (20, 60),
    ("POST", "/api/admin/auth/login"): (10, 300),
}
MAX_REQUEST_BODY_BYTES = 2 * 1024 * 1024


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        started = perf_counter()
        oversized = _oversized_response(request)
        if oversized is not None:
            response = oversized
        else:
            limited = await _rate_limit_response(request)
            response = limited if limited is not None else await call_next(request)

        _add_security_headers(response)
        route = request.scope.get("route")
        route_path = getattr(route, "path", request.url.path)
        runtime_metrics.observe_http(
            method=request.method,
            route=route_path,
            status_code=response.status_code,
            duration_seconds=perf_counter() - started,
        )
        return response


def _oversized_response(request: Request) -> Response | None:
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


async def _rate_limit_response(request: Request) -> Response | None:
    policy = RATE_LIMITED_ROUTES.get((request.method, request.url.path))
    if policy is None:
        return None

    limit, window_seconds = policy
    window = int(time()) // window_seconds
    identity = request.client.host if request.client else "unknown"
    key = f"dialog_spy:rate_limit:{request.method}:{request.url.path}:{identity}:{window}"
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
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


def _add_security_headers(response: Response) -> None:
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
