from pathlib import Path


def test_bot_daily_pulse_is_visual_and_registered() -> None:
    handler = Path("app/bot/engagement_handlers.py").read_text(encoding="utf-8")
    setup = Path("app/bot/setup.py").read_text(encoding="utf-8")
    assert 'Command("today")' in handler
    assert '"user:today"' in handler
    assert "answer_photo" in handler
    assert "PHANTOM PULSE" in handler
    assert "Что произошло за 24 часа" in handler
    assert "dispatcher.include_router(engagement_router)" in setup


def test_daily_pulse_button_is_admin_configurable() -> None:
    menu = Path("app/bot/enhanced_user_menu.py").read_text(encoding="utf-8")
    editor = Path("app/bot/menu_editor_handlers.py").read_text(encoding="utf-8")
    assert '"show_today"' in menu
    assert 'text="✨ Что сегодня"' in menu
    assert '"show_today": "Что сегодня"' in editor


def test_miniapp_pulse_is_single_runtime_and_uses_live_intelligence() -> None:
    index = Path("app/static/miniapp/index.html").read_text(encoding="utf-8")
    js = Path("app/static/miniapp/engagement-layer.js").read_text(encoding="utf-8")
    assert index.count("engagement-layer.js") == 1
    assert index.count("engagement-layer.css") == 1
    assert "/api/intelligence?days=7" in js
    assert "MutationObserver" in js
    assert "mounted" in js
    assert "data-go=\"stats\"" in js
