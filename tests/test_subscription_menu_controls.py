from pathlib import Path


def test_user_menu_has_subscription_and_visibility_flags() -> None:
    source = Path("app/bot/enhanced_user_menu.py").read_text(encoding="utf-8")
    for key in (
        "show_mini_app",
        "show_stats",
        "show_subscription",
        "show_profile",
        "show_settings",
        "show_instruction",
        "show_offer",
    ):
        assert key in source
    assert 'text="💎 Подписка"' in source
    assert 'callback_data="user:subscription"' in source


def test_subscription_can_be_opened_and_auto_renew_disabled() -> None:
    source = Path("app/bot/user_handlers.py").read_text(encoding="utf-8")
    assert "def subscription_keyboard" in source
    assert 'callback_data="user:subscription:cancel"' in source
    assert 'callback_data="impaya:pay"' in source
    assert 'section == "subscription"' in source
    assert "cancel_subscription(callback.from_user.id)" in source
    assert "Payment.recurring.is_(True)" in source


def test_admin_menu_editor_toggles_every_user_button() -> None:
    source = Path("app/bot/menu_editor_handlers.py").read_text(encoding="utf-8")
    assert "BUTTONS =" in source
    assert 'callback_data=f"menuedit:toggle:{key}"' in source
    assert 'command == "toggle"' in source
    for label in ("Mini App", "Статистика", "Подписка", "Профиль", "Настройки", "Инструкция", "Оферта"):
        assert label in source
