#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

printf '\n[1/6] Проверка Python\n'
python3 -m compileall -q backend/app

printf '\n[2/6] Проверка JavaScript\n'
if command -v node >/dev/null 2>&1; then
  node --check web/app.js
  node --check web/admin.js
else
  echo "Node.js не установлен на хосте — JavaScript будет проверен внутри web-сборки."
fi

printf '\n[3/6] Проверка shell-скриптов\n'
bash -n scripts/*.sh

printf '\n[4/6] Проверка Docker Compose\n'
docker compose config >/dev/null

printf '\n[5/6] Сборка образов\n'
docker compose build api worker web

printf '\n[6/6] Тесты проекта\n'
# API-образ содержит только backend/app и backend/tests. Тесты интерфейса также
# читают /project/web, поэтому монтируем полный корень проекта в read-only режиме.
docker compose run --rm \
  --no-deps \
  -v "$ROOT_DIR:/project:ro" \
  -w /project/backend \
  api pytest -q tests

printf '\nDialog Spy v0.8.8 verification passed.\n'
