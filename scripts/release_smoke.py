from __future__ import annotations

import argparse
import sys

import httpx

CHECKS = (
    ("/health/live", "application/json"),
    ("/health/ready", "application/json"),
    ("/metrics", "text/plain"),
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run post-deployment smoke checks.")
    parser.add_argument(
        "base_url",
        help="Deployment base URL, for example https://app.example.com",
    )
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    failures: list[str] = []
    with httpx.Client(timeout=args.timeout, follow_redirects=False) as client:
        for path, expected_type in CHECKS:
            url = f"{base_url}{path}"
            try:
                response = client.get(url)
                response.raise_for_status()
            except Exception as exc:
                failures.append(f"{path}: {exc}")
                continue
            content_type = response.headers.get("content-type", "")
            if expected_type not in content_type:
                failures.append(
                    f"{path}: expected {expected_type!r} content type, got {content_type!r}"
                )
                continue
            print(f"OK {path} [{response.status_code}] {content_type}")

    if failures:
        for failure in failures:
            print(f"FAIL {failure}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
