from pathlib import Path


def test_admin_route_serves_full_control_center_directly() -> None:
    source = Path("app/main.py").read_text(encoding="utf-8")
    route = source.split('@app.get("/admin", include_in_schema=False)', 1)[1].split(
        '@app.get("/admin/platform"', 1
    )[0]
    assert '"app/static/admin/index.html"' in route
    assert '"app/static/admin/stable.html"' not in route


def test_full_control_center_is_self_contained() -> None:
    source = Path("app/static/admin/index.html").read_text(encoding="utf-8")
    assert "Phantom Control Center" in source
    assert 'id="loginForm"' in source
    assert 'id="dashboard"' in source
    assert 'id="users"' in source
    assert 'id="billing"' in source
    assert "sessionStorage.getItem('adminToken')" in source
    assert "<iframe" not in source


def test_admin_assets_remain_available() -> None:
    source = Path("app/main.py").read_text(encoding="utf-8")
    assert '@app.get("/admin/{asset_path:path}"' in source
    assert 'Path("app/static/admin") / asset_path' in source
