from pathlib import Path


def test_admin_shell_avoids_browser_global_collisions() -> None:
    source = Path("app/static/admin/stable.html").read_text(encoding="utf-8")
    assert "const frames=" not in source
    assert "const frameMap=" in source
    assert "frame.src='about:blank'" in source
    assert "frame.src.endsWith('/admin')" in source


def test_admin_shell_validates_login_token_and_has_visible_failure_state() -> None:
    source = Path("app/static/admin/stable.html").read_text(encoding="utf-8")
    assert "if(!data.access_token)" in source
    assert "showError" in source
    assert "Раздел загружается слишком долго" in source
    assert "location.replace('/admin?v=3.0.2')" in source


def test_admin_shell_default_assets_exist() -> None:
    source = Path("app/static/admin/stable.html").read_text(encoding="utf-8")
    assets = (
        "operations.html",
        "dialogs-media.html",
        "platform.html",
        "user360-v2.html",
        "billing-v2-1.html",
        "funnel.html",
        "index.html",
    )
    root = Path("app/static/admin")
    for asset in assets:
        assert asset in source
        assert (root / asset).is_file(), asset


def test_admin_routes_serve_shell_and_assets() -> None:
    source = Path("app/main.py").read_text(encoding="utf-8")
    assert '"app/static/admin/stable.html"' in source
    assert '@app.get("/admin/{asset_path:path}"' in source
    assert 'Path("app/static/admin") / asset_path' in source
