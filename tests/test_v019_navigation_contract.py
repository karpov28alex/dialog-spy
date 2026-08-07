from pathlib import Path


def test_root_menu_is_compact_and_secondary_actions_are_nested() -> None:
    source = Path("app/bot/enhanced_user_menu.py").read_text(encoding="utf-8")
    assert "✨ Что сегодня" not in source
    assert "📖 Инструкция" not in source
    assert "📄 Оферта" not in source
    assert "📱 Открыть Mini App" in source
    assert "👤 Мой профиль" in source
    assert "📊 Статистика" in source
    assert "⚙️ Настройки" in source


def test_v019_navigation_replaces_old_messages_and_nests_subscription() -> None:
    source = Path("app/bot/navigation_v019.py").read_text(encoding="utf-8")
    setup = Path("app/bot/setup.py").read_text(encoding="utf-8")
    assert "await callback.message.delete()" in source
    assert "💎 Подписка" in source
    assert "📄 Оферта" in source
    assert source.count("↩️ Вернуться в профиль") >= 2
    assert "engagement:recap:1" in source
    assert "engagement:recap:7" in source
    navigation_mount = "dispatcher.include_router(navigation_v019_router)"
    engagement_mount = "dispatcher.include_router(engagement_router)"
    assert setup.index(navigation_mount) < setup.index(engagement_mount)


def test_subscription_admin_switch_remains_shared_with_miniapp() -> None:
    editor = Path("app/bot/menu_editor_handlers.py").read_text(encoding="utf-8")
    menu = Path("app/bot/enhanced_user_menu.py").read_text(encoding="utf-8")
    assert '"show_subscription": "Подписка и оферта"' in editor
    assert "одновременно управляет ботом и Mini App" in editor
    assert "subscription_commerce_config" in menu
