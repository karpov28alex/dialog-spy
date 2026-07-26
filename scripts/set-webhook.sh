#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
set -a
source .env
set +a

HEALTH_URL="${PUBLIC_BASE_URL%/}/api/health"
WEBHOOK_URL="${PUBLIC_BASE_URL%/}/api/telegram/webhook/${WEBHOOK_SECRET}"

curl -fsS "$HEALTH_URL" >/dev/null

telegram_call() {
  local response
  response="$(curl -fsS "$@")"
  printf '%s\n' "$response" | python3 -c 'import json,sys; data=json.load(sys.stdin); print(json.dumps(data,ensure_ascii=False,indent=2)); raise SystemExit(0 if data.get("ok") else 1)'
}

telegram_call "https://api.telegram.org/bot${BOT_TOKEN}/deleteWebhook?drop_pending_updates=false"
telegram_call -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -H 'Content-Type: application/json' \
  -d "{\"url\":\"${WEBHOOK_URL}\",\"allowed_updates\":[\"message\",\"callback_query\",\"business_connection\",\"business_message\",\"edited_business_message\",\"deleted_business_messages\"],\"drop_pending_updates\":false}"
telegram_call "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo"
