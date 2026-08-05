from pathlib import Path


def test_global_search_is_available_on_every_admin_page() -> None:
    source = Path("app/static/admin/global-tabs.js").read_text(encoding="utf-8")
    assert "data-global-search-button" in source
    assert "data-phantom-command" in source
    assert "Ctrl K" in source
    assert "event.key === '/'" in source


def test_global_search_combines_users_and_dialogs() -> None:
    source = Path("app/static/admin/global-tabs.js").read_text(encoding="utf-8")
    assert "/api/admin/user360/search?q=" in source
    assert "/api/admin/dialog-viewer/dialogs?search=" in source
    assert "Promise.all" in source
    assert "/admin/user360-mobile.html?user_id=" in source
    assert "/admin/dialogs-media.html?user_id=" in source


def test_global_search_has_operational_quick_actions() -> None:
    source = Path("app/static/admin/global-tabs.js").read_text(encoding="utf-8")
    assert "Быстрые действия" in source
    assert "Финансовая операция" in source
    assert "Проверить систему" in source
    assert "cache: 'no-store'" in source
