from pathlib import Path

from app.modules.account.router import router as account_router
from app.modules.account.schemas import ProfileResponse, SubscriptionResponse
from app.modules.admin.router import router as admin_router
from app.modules.admin.schemas import AdminDashboardResponse


def test_account_routes_are_typed() -> None:
    routes = {route.path: route for route in account_router.routes}
    assert routes["/me"].response_model is ProfileResponse
    assert routes["/subscription"].response_model is SubscriptionResponse
    assert "/settings" in routes


def test_admin_v2_dashboard_is_typed() -> None:
    route = next(route for route in admin_router.routes if route.path.endswith("/dashboard"))
    assert route.response_model is AdminDashboardResponse


def test_user_route_is_only_a_compatibility_shell() -> None:
    source = Path("app/api/routes/user.py").read_text(encoding="utf-8")
    assert "select(" not in source
    assert "BaseModel" not in source
    assert "account_router" in source
    assert "legacy_archive_router" in source
    assert "admin_v2_router" in source


def test_account_and_admin_services_have_no_fastapi_dependency() -> None:
    account = Path("app/modules/account/service.py").read_text(encoding="utf-8")
    admin = Path("app/modules/admin/service.py").read_text(encoding="utf-8")
    assert "fastapi" not in account
    assert "fastapi" not in admin
