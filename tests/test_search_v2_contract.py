from pathlib import Path

from app.api.routes.global_search import router
from app.modules.search.schemas import SearchResponse


def test_search_route_is_typed() -> None:
    route = next(route for route in router.routes if route.path == "/api/search")
    assert route.response_model is SearchResponse


def test_search_route_delegates_to_domain_module() -> None:
    source = Path("app/api/routes/global_search.py").read_text(encoding="utf-8")
    assert "SearchService" in source
    assert "SearchRepository" in source
    assert "select(" not in source


def test_search_module_has_no_http_dependency() -> None:
    service = Path("app/modules/search/service.py").read_text(encoding="utf-8")
    repository = Path("app/modules/search/repository.py").read_text(encoding="utf-8")
    assert "fastapi" not in service
    assert "fastapi" not in repository
