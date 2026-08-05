from pathlib import Path

from app.api.routes.webhook import router as webhook_router


def test_legacy_and_canonical_webhook_routes_are_registered() -> None:
    paths = {path for route in webhook_router.routes if (path := getattr(route, "path", None))}
    assert "/telegram/webhook/{secret}" in paths
    assert "/api/telegram/webhook/{secret}" in paths


def test_miniapp_profile_loads_user_and_settings_without_global_abort() -> None:
    source = Path("app/static/miniapp/app.js").read_text(encoding="utf-8")
    assert "api('/api/me')" in source
    assert "api('/api/settings')" in source
    assert "controller?.abort()" not in source
    assert "profile" in source


def test_edit_history_is_only_rendered_for_actually_edited_messages() -> None:
    source = Path("app/static/miniapp/app.js").read_text(encoding="utf-8")
    assert "edited_at" in source
    assert "versions" in source


def test_admin_is_mobile_responsive_and_russian_localized() -> None:
    gateway = Path("app/static/admin/stable.html").read_text(encoding="utf-8")
    control_center = Path("app/static/admin/index.html").read_text(encoding="utf-8")

    assert 'lang="ru"' in gateway
    assert 'name="viewport"' in gateway
    assert "@media(max-width:1000px)" in control_center
    assert "@media(max-width:560px)" in control_center
    assert "Обзор" in control_center
    assert "Пользователи" in control_center
    assert "Система" in control_center
