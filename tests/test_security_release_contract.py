from pathlib import Path

from starlette.requests import Request
from starlette.responses import Response

from app.observability.middleware import (
    MAX_REQUEST_BODY_BYTES,
    RATE_LIMITED_ROUTES,
    _add_security_headers,
    _oversized_response,
)


def _request(*, content_length: str | None = None) -> Request:
    headers = []
    if content_length is not None:
        headers.append((b"content-length", content_length.encode()))
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/auth/telegram",
            "headers": headers,
            "client": ("127.0.0.1", 12345),
            "scheme": "http",
            "server": ("test", 80),
            "query_string": b"",
        }
    )


def test_sensitive_login_routes_are_rate_limited() -> None:
    assert ("POST", "/api/auth/telegram") in RATE_LIMITED_ROUTES
    assert ("POST", "/api/admin/auth/login") in RATE_LIMITED_ROUTES


def test_large_request_is_rejected_before_body_read() -> None:
    response = _oversized_response(_request(content_length=str(MAX_REQUEST_BODY_BYTES + 1)))
    assert response is not None
    assert response.status_code == 413


def test_security_headers_are_added() -> None:
    response = Response()
    _add_security_headers(response)
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "camera=()" in response.headers["permissions-policy"]


def test_release_tooling_is_present() -> None:
    assert Path(".pre-commit-config.yaml").is_file()
    assert Path("scripts/check_migrations.py").is_file()
    assert Path("scripts/release_smoke.py").is_file()
