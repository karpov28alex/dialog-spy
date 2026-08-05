from pathlib import Path


def test_user360_removes_cached_legacy_overlay() -> None:
    source = Path("app/static/admin/user360-mobile.html").read_text(encoding="utf-8")
    assert "data-user360-native" in source
    assert "data-user360-extra" in source
    assert "MutationObserver(purgeLegacy)" in source
    assert "purgeLegacy()" in source


def test_user360_hides_technical_referral_status() -> None:
    source = Path("app/static/admin/user360-mobile.html").read_text(encoding="utf-8")
    assert "referral:'По приглашению'" in source
    assert "В старой записи не сохранён ID пригласившего" in source
    assert "Прямое подключение" in source


def test_user360_metrics_remain_clickable() -> None:
    source = Path("app/static/admin/user360-mobile.html").read_text(encoding="utf-8")
    assert "data-detail" in source
    assert "data-open-user" in source
    assert "openReferrer" in source
    assert "/admin/dialogs-media.html?user_id=" in source
