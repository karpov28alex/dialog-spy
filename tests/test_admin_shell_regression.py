from pathlib import Path


def test_admin_gateway_does_not_use_iframes() -> None:
    source = Path("app/static/admin/stable.html").read_text(encoding="utf-8")
    assert "<iframe" not in source
    assert "frameMap" not in source
    assert "about:blank" not in source


def test_admin_gateway_redirects_to_full_control_center() -> None:
    source = Path("app/static/admin/stable.html").read_text(encoding="utf-8")
    assert "'/admin/index.html?v=3.0.3'" in source
    assert "sessionStorage.setItem('adminToken'" in source
    assert "localStorage.setItem('adminToken'" in source
    assert "if(!data.access_token)" in source


def test_full_control_center_exists_and_is_self_contained() -> None:
    source = Path("app/static/admin/index.html").read_text(encoding="utf-8")
    assert "Phantom Control Center" in source
    assert 'id="dashboard"' in source
    assert 'id="users"' in source
    assert 'id="billing"' in source
    assert "sessionStorage.getItem('adminToken')" in source


def test_admin_routes_serve_gateway_and_assets() -> None:
    source = Path("app/main.py").read_text(encoding="utf-8")
    assert '"app/static/admin/stable.html"' in source
    assert '@app.get("/admin/{asset_path:path}"' in source
    assert 'Path("app/static/admin") / asset_path' in source
