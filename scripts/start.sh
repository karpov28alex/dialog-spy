#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
systemctl start docker 2>/dev/null || true
docker compose up -d --remove-orphans
sleep 8
docker compose ps
