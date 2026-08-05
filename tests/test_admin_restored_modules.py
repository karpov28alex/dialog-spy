from pathlib import Path


def test_working_admin_loads_restored_module_navigation() -> None:
    source = Path("app/main.py").read_text(encoding="utf-8")
    assert 'Path("app/static/admin/index.html").read_text' in source
    assert '"/admin/restore-modules.js?v=1"' in source
    assert "HTMLResponse" in source


def test_restored_modules_use_direct_navigation_without_iframes() -> None:
    source = Path("app/static/admin/restore-modules.js").read_text(encoding="utf-8")
    assert "<iframe" not in source
    assert "window.location.assign" in source
    assert "/admin/user360-mobile.html" in source
    assert "/admin/dialogs-media.html" in source
    assert "/admin/platform.html" in source
    assert "/admin/operations.html" in source
    assert "/admin/billing-mobile.html" in source
    assert "/admin/funnel.html" in source
