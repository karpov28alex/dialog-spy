from pathlib import Path


def test_root_user_menu_is_compact() -> None:
    source = Path("app/bot/enhanced_user_menu.py").read_text(encoding="utf-8")
    for label in ("Открыть Mini App", "Мой профиль", "Статистика", "Настройки", "Админ-панель"):
        assert label in source
    for label in ("Подписка", "Инструкция", "Оферта", "Что сегодня"):
        assert label not in source


def test_secondary_sections_are_nested_in_v019_navigation() -> None:
    source = Path("app/bot/navigation_v019.py").read_text(encoding="utf-8")
    assert "💎 Подписка" in source
    assert "📖 Инструкция" in source
    assert "📄 Оферта" in source
    assert "engagement:recap:1" in source
    assert "engagement:recap:7" in source
    assert "↩️ Вернуться в профиль" in source


def test_handlers_for_compact_menu_are_mounted() -> None:
    setup = Path("app/bot/setup.py").read_text(encoding="utf-8")
    assert "dispatcher.include_router(navigation_v019_router)" in setup
    assert "dispatcher.include_router(product_experience_router)" in setup
    assert "dispatcher.include_router(profile_card_router)" in setup
    assert "dispatcher.include_router(menu_editor_router)" in setup


def test_subscription_visibility_remains_admin_configurable() -> None:
    menu = Path("app/bot/enhanced_user_menu.py").read_text(encoding="utf-8")
    editor = Path("app/bot/menu_editor_handlers.py").read_text(encoding="utf-8")
    assert "show_subscription" in menu
    assert '"show_subscription": "Подписка и оферта"' in editor
    assert 'callback_data=f"menuedit:toggle:{field}"' in editor
    assert "subscription_commerce_config" in menu


def test_access_gate_does_not_hide_informational_sections() -> None:
    middleware = Path("app/bot/channel_gate_middleware.py").read_text(encoding="utf-8")
    product = Path("app/bot/product_experience_handlers.py").read_text(encoding="utf-8")
    profile = Path("app/bot/profile_card_handlers.py").read_text(encoding="utf-8")
    for command in ("/menu", "/profile", "/settings", "/stats", "/help", "/subscription"):
        assert command in middleware
    assert "Все разделы Phantom уже доступны" in product
    assert "Статистика пока не собрана" in product
    assert "Phantom ещё не подключён к автоматизации чатов" in profile


def test_recap_menu_has_no_share_dialogs_or_analytics_buttons() -> None:
    source = Path("app/bot/engagement_handlers.py").read_text(encoding="utf-8")
    keyboard = source[source.index("def _keyboard"):source.index("def _caption")]
    assert "🚀 Поделиться" not in keyboard
    assert "💬 Диалоги" not in keyboard
    assert "📊 Аналитика" not in keyboard


def test_recap_callbacks_delete_current_message_before_rendering_next() -> None:
    source = Path("app/bot/engagement_handlers.py").read_text(encoding="utf-8")
    assert "async def _replace(callback: CallbackQuery)" in source
    for handler in ("today_callback", "recap_callback"):
        block = source[source.index(f"async def {handler}"):]
        block = block.split("\n\n@router", 1)[0]
        assert "await _replace(callback)" in block
        assert block.index("await _replace(callback)") < block.index("await _send(target")
