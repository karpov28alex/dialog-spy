#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
[[ -f .env ]] || { echo 'ERROR: cp .env.example .env and fill it first'; exit 1; }
chmod +x scripts/*.sh
./scripts/verify.sh
docker compose up -d --remove-orphans
sleep 10
./scripts/set-webhook.sh
./scripts/doctor.sh
