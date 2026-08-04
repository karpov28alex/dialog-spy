from datetime import UTC, datetime
from pathlib import Path

from app.api.routes.global_search import router
from app.modules.search.schemas import SearchFilters, SearchResponse


def test_search_route_is_typed() -> None:
    route = next(route for route in router.routes if route.path == "/api/search")
    assert route.response_model is SearchResponse


def test_search_route_delegates_to_domain_module() -> None:
    source = Path("app/api/routes/global_search.py").read_text(encoding="utf-8")
    assert "SearchService" in source
    assert "SearchRepository" in source
    assert "SearchFilters" in source
    assert "select(" not in source


def test_search_module_has_no_http_dependency() -> None:
    service = Path("app/modules/search/service.py").read_text(encoding="utf-8")
    repository = Path("app/modules/search/repository.py").read_text(encoding="utf-8")
    assert "fastapi" not in service
    assert "fastapi" not in repository


def test_search_contract_supports_filters_and_cursor() -> None:
    cursor = datetime(2026, 1, 1, tzinfo=UTC)
    filters = SearchFilters(kinds=["message", "media"], dialog_id=42, cursor=cursor)
    assert filters.kinds == ["message", "media"]
    assert filters.dialog_id == 42
    assert filters.cursor == cursor


def test_repository_uses_postgresql_ranked_search() -> None:
    source = Path("app/modules/search/repository.py").read_text(encoding="utf-8")
    assert "websearch_to_tsquery" in source
    assert "ts_rank_cd" in source
    assert "similarity" in source


def test_search_migration_adds_trigram_and_fts_indexes() -> None:
    source = Path("alembic/versions/0006_search_indexes.py").read_text(encoding="utf-8")
    assert "CREATE EXTENSION IF NOT EXISTS pg_trgm" in source
    assert "gin_trgm_ops" in source
    assert "to_tsvector('simple'" in source
