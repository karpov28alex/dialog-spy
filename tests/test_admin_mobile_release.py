from pathlib import Path


def test_user360_mobile_uses_explicit_dom_references() -> None:
    source = Path("app/static/admin/user360-mobile.html").read_text(encoding="utf-8")
    assert "document.getElementById('query')" in source
    assert "document.getElementById('results')" in source
    assert "user360/search?q=" in source
    assert "window.results" not in source


def test_billing_mobile_renders_cards_not_wide_table() -> None:
    source = Path("app/static/admin/billing-mobile.html").read_text(encoding="utf-8")
    assert "<table" not in source
    assert 'class="payment"' in source
    assert "/api/admin/impaya/overview" in source
    assert "/api/admin/impaya/payments" in source


def test_restored_navigation_prefers_mobile_views() -> None:
    source = Path("app/static/admin/restore-modules.js").read_text(encoding="utf-8")
    assert "/admin/user360-mobile.html" in source
    assert "/admin/billing-mobile.html" in source
    assert "/admin/user360-v2.html" not in source
    assert "/admin/billing-v2-1.html" not in source


def test_mobile_runtime_reports_errors_and_adapts_tables() -> None:
    runtime = Path("app/static/admin/admin-runtime.js").read_text(encoding="utf-8")
    styles = Path("app/static/admin/admin-mobile.css").read_text(encoding="utf-8")
    assert "unhandledrejection" in runtime
    assert "admin-mobile-table" in runtime
    assert ".admin-mobile-table" in styles
