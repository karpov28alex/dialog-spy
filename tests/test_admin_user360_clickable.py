from pathlib import Path


def test_user360_exposes_clickable_metrics_and_details() -> None:
    source = Path("app/static/admin/user360-mobile.html").read_text(encoding="utf-8")
    assert 'data-user360-native="true"' in source
    assert 'data-detail="${x[2]}"' in source
    assert "Пригласил:" in source
    assert "Защищённые медиа" in source
    assert "Оплачено всего" in source
    assert "Средний чек" in source
    assert "Приглашено" in source
    assert "Активные подключения" in source
    assert "renderDetail" in source
    assert "/admin/dialogs-media.html?user_id=" in source


def test_global_tabs_use_native_user360_without_legacy_overlay() -> None:
    source = Path("app/static/admin/global-tabs.js").read_text(encoding="utf-8")
    assert "user360-mobile.html?v=6" in source
    assert "renderExtra" not in source
    assert "data-open-referrer" not in source
