from pathlib import Path


def test_dialog_viewer_can_filter_by_archive_owner() -> None:
    source = Path("app/static/admin/global-tabs.js").read_text(encoding="utf-8")
    assert "data-owner-filter" in source
    assert "/api/admin/dialog-archive/users" in source
    assert "/api/admin/users/${owner.id}/dialogs" in source
    assert "Архив владельца" in source
    assert "Выбран владелец" in source
    assert "loadDialogs();" in source


def test_dialog_owner_filter_supports_direct_links_and_user360() -> None:
    source = Path("app/static/admin/global-tabs.js").read_text(encoding="utf-8")
    assert "url.searchParams.set('user_id'" in source
    assert "new URLSearchParams(window.location.search).get('user_id')" in source
    assert "/admin/user360-mobile.html?user_id=${owner.id}" in source


def test_dialog_owner_filter_does_not_depend_on_window_page_helpers() -> None:
    source = Path("app/static/admin/global-tabs.js").read_text(encoding="utf-8")
    assert "window.avatar" not in source
    assert "window.shortTime" not in source
    assert "window.openDialog" not in source
    assert "renderAvatar" in source
    assert "shortDate" in source
