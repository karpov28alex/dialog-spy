from pathlib import Path


def test_global_tabs_remove_legacy_dashboard_navigation() -> None:
    source = Path("app/static/admin/global-tabs.js").read_text(encoding="utf-8")
    assert ".side, .nav, .top #logout" in source
    assert "shell.style.display = 'block'" in source


def test_user360_shows_inviter_and_extended_metrics() -> None:
    source = Path("app/static/admin/user360-mobile.html").read_text(encoding="utf-8")
    assert "Пригласил:" in source
    assert "referrer_user_id" in source
    assert "Защищённые медиа" in source
    assert "Оплачено всего" in source
    assert "Средний чек" in source
    assert "Активные подключения" in source
    assert "data-detail" in source
    assert "user_id" in source


def test_deprecated_business_user_wording_is_not_added() -> None:
    tabs = Path("app/static/admin/global-tabs.js").read_text(encoding="utf-8")
    user360 = Path("app/static/admin/user360-mobile.html").read_text(encoding="utf-8")
    source = tabs + user360
    assert "бизнес-пользовател" not in source.lower()
    assert "Активные подключения" in source
