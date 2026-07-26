#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a
fail=0
run(){ printf '\n=== %s ===\n' "$1"; shift; "$@" || fail=1; }
run "containers" docker compose ps
run "local health" curl -fsS --max-time 10 http://127.0.0.1:8081/api/health
run "public health" curl -fsS --max-time 10 "${PUBLIC_BASE_URL%/}/api/health"
run "webhook route" curl -fsS --max-time 10 -X POST "${PUBLIC_BASE_URL%/}/api/telegram/webhook/${WEBHOOK_SECRET}" -H 'Content-Type: application/json' -d "{\"update_id\":$(( $(date +%s) + 900000000 ))}"
run "webhook info" curl -fsS "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo"
printf '\n=== worker logs ===\n'; docker compose logs --tail=40 worker || true
printf '\n=== api logs ===\n'; docker compose logs --tail=80 api || true
exit "$fail"
