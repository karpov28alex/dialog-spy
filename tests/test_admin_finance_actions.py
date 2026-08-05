from pathlib import Path


def test_global_tabs_hide_legacy_home_navigation() -> None:
    source = Path("app/static/admin/global-tabs.js").read_text(encoding="utf-8")
    assert "pathname === '/admin'" in source
    assert "document.querySelectorAll('.nav')" in source
    assert "element.hidden = true" in source


def test_mobile_billing_exposes_real_manual_charge_flow() -> None:
    source = Path("app/static/admin/billing-mobile.html").read_text(encoding="utf-8")
    assert "/api/admin/user360/search" in source
    assert "/api/admin/impaya/manual-charge/prepare" in source
    assert "/api/admin/impaya/manual-charge/" in source
    assert "/confirm" in source
    assert "confirmation_code" in source
    assert "Списать" in source
