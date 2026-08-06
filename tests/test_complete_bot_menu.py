from pathlib import Path


def test_complete_user_menu_keeps_all_product_sections() -> None:
    source = Path("app/bot/enhanced_user_menu.py").read_text(encoding="utf-8")

    for label in (
        "Открыть Mini App",
        "Статистика",
        "Подписка",
        "Профиль",
        "Настройки",
        "Инструкция",
        "Оферта",
        "Админ-панель",
    ):
        assert label in source

    for callback in (
        'callback_data="user:stats"',
        'callback_data="user:subscription"',
        'callback_data="user:profile"',
        'callback_data="user:settings"',
        'callback_data="help"',
        'callback_data="crm:home"',
    ):
        assert callback in source


def test_welcome_and_statistics_use_the_complete_keyboard() -> None:
    source = Path("app/bot/product_experience_handlers.py").read_text(encoding="utf-8")

    assert "from app.bot.enhanced_user_menu import enhanced_user_keyboard" in source
    assert "reply_markup=enhanced_user_keyboard(await is_admin(user.telegram_id))" in source
    assert "rows = [list(row) for row in enhanced_user_keyboard(admin).inline_keyboard]" in source
    assert "reply_markup=_stats_keyboard(await is_admin(telegram_id))" in source
    assert "from app.bot.admin_console import is_admin, user_menu" not in source


def test_handlers_for_restored_menu_are_mounted() -> None:
    setup = Path("app/bot/setup.py").read_text(encoding="utf-8")
    editor = Path("app/bot/menu_editor_handlers.py").read_text(encoding="utf-8")
    experience = Path("app/bot/user_experience_handlers.py").read_text(encoding="utf-8")

    assert "dispatcher.include_router(product_experience_router)" in setup
    assert "dispatcher.include_router(profile_card_router)" in setup
    assert "dispatcher.include_router(menu_editor_router)" in setup
    assert 'F.data == "user:settings"' in editor
    assert 'F.data == "user:subscription"' in editor
    assert 'F.data == "user:subscription:cancel"' in editor
    assert "cancel_subscription" in editor
    assert 'F.data == "help"' in experience


def test_admin_can_toggle_every_user_menu_button() -> None:
    menu = Path("app/bot/enhanced_user_menu.py").read_text(encoding="utf-8")
    editor = Path("app/bot/menu_editor_handlers.py").read_text(encoding="utf-8")

    fields = (
        "show_miniapp",
        "show_stats",
        "show_subscription",
        "show_profile",
        "show_settings",
        "show_instruction",
        "show_offer",
    )
    for field in fields:
        assert field in menu
        assert field in editor

    assert 'callback_data=f"menuedit:toggle:{field}"' in editor
    assert "изменения применяются сразу" in editor.lower()
