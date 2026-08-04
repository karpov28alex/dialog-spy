.PHONY: install dev up down logs test lint typecheck check migrate webhook backup

install:
	python -m pip install -e '.[dev]'

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=200 api worker

test:
	pytest -q

lint:
	ruff check .

typecheck:
	mypy app

check: lint typecheck test

migrate:
	alembic upgrade head

webhook:
	python scripts/set_webhook.py

backup:
	bash scripts/backup.sh
