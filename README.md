# Dialog Spy / Phantom

Telegram Business archive service with a FastAPI backend, Telegram Mini App, administrative workspace, PostgreSQL storage, Redis-backed processing, message history, media recovery and archive-wide search.

## Stack

- Python 3.12, FastAPI, aiogram
- SQLAlchemy asyncio, PostgreSQL, Alembic
- Redis
- Static Telegram Mini App and admin interfaces
- pytest, Ruff and mypy

## Start locally

```bash
cp .env.example .env
make install
make migrate
make dev
```

For the containerized environment:

```bash
make up
make logs
```

## Useful endpoints

- `GET /health/live` — process and release metadata
- `GET /health/ready` — PostgreSQL and Redis readiness
- `/app` — Telegram Mini App
- `/admin` — administrative interface
- `/docs` — OpenAPI documentation in development

## Development

Run all quality checks with:

```bash
make check
```

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) and [docs/PRODUCTION_ARCHITECTURE.md](docs/PRODUCTION_ARCHITECTURE.md).

## Release direction

The current foundation release is `0.14.0`. The next major workstreams are frontend consolidation, typed API contracts, Search V2, administrative session hardening and expanded observability.
