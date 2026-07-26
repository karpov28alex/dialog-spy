#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
# bootstrap synchronizes ADMIN_EMAIL and ADMIN_PASSWORD from .env.
docker compose exec -T api python -m app.bootstrap
