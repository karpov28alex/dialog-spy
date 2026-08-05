from pathlib import Path


def test_all_admin_html_responses_receive_global_tabs() -> None:
    source = Path("app/main.py").read_text(encoding="utf-8")
    assert "_ADMIN_TABS_STYLE" in source
    assert "_ADMIN_TABS_SCRIPT" in source
    assert "def _admin_html_response" in source
    assert 'if path.suffix.lower() == ".html"' in source
    assert "return _admin_html_response(path)" in source
    assert '_admin_html_response("app/static/admin/unified.html")' in source
    assert '_admin_html_response("app/static/admin/dialogs-media.html")' in source


def test_global_tabs_cover_every_restored_module() -> None:
    source = Path("app/static/admin/global-tabs.js").read_text(encoding="utf-8")
    expected = (
        "/admin",
        "/admin/user360-mobile.html",
        "/admin/dialogs-media.html",
        "/admin/platform.html",
        "/admin/operations.html",
        "/admin/billing-mobile.html",
        "/admin/funnel.html",
    )
    for route in expected:
        assert route in source
    assert "aria-current" in source
    assert "scrollIntoView" in source
    assert "localStorage.removeItem('adminToken')" in source


def test_global_tabs_are_sticky_and_mobile_scrollable() -> None:
    source = Path("app/static/admin/global-tabs.css").read_text(encoding="utf-8")
    assert "position:sticky" in source
    assert "overflow-x:auto" in source
    assert "-webkit-overflow-scrolling:touch" in source
    assert "@media(max-width:700px)" in source
