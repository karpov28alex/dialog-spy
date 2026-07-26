#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
mkdir -p /root/dialogspy-backups
if docker compose ps postgres --status running >/dev/null 2>&1; then docker compose exec -T postgres pg_dump -U dialogspy -d dialogspy > "/root/dialogspy-backups/dialogspy-$(date +%F-%H%M%S).sql"; fi
docker compose build --no-cache api worker web
docker compose up -d --force-recreate --remove-orphans
sleep 10
./scripts/doctor.sh
