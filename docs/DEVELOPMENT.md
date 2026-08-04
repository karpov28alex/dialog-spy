# Development

## Requirements

- Python 3.12+
- PostgreSQL
- Redis
- Docker Compose (recommended)

## Local setup

```bash
cp .env.example .env
make install
make migrate
make dev
```

The API is available at `http://localhost:8000`, Mini App at `/app`, admin UI at `/admin`.

## Quality checks

```bash
make check
```

Run database migrations before starting the application after pulling schema changes.

## Release version

The canonical runtime version is stored in `app/version.py`. Keep the package version in `pyproject.toml` aligned during a release.

## Architecture rules

- FastAPI routes should validate input and delegate business logic.
- Database queries belong in services or repositories as domains are extracted.
- New API responses should use Pydantic response models.
- Every user-owned query must filter by the authenticated owner.
- Schema changes require an Alembic migration and tests.
