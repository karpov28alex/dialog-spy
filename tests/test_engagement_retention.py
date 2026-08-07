from pathlib import Path


def test_bot_daily_and_weekly_recaps_are_visual_and_registered() -> None:
    handler = Path("app/bot/engagement_handlers.py").read_text(encoding="utf-8")
    setup = Path("app/bot/setup.py").read_text(encoding="utf-8")
    assert 'Command("today")' in handler
    assert 'Command("week", "weekly")' in handler
    assert '"user:today"' in handler
    assert "answer_photo" in handler
    assert "PHANTOM DAILY" in handler
    assert "PHANTOM WEEKLY" in handler
    assert "Что произошло за 24 часа" in handler
    assert "Ваша неделя в Phantom" in handler
    assert "engagement:share:" in handler
    assert "referral_url" in handler
    assert "Серия активности" in handler
    assert "dispatcher.include_router(engagement_router)" in setup


def test_daily_pulse_button_is_admin_configurable() -> None:
    menu = Path("app/bot/enhanced_user_menu.py").read_text(encoding="utf-8")
    editor = Path("app/bot/menu_editor_handlers.py").read_text(encoding="utf-8")
    assert '"show_today"' in menu
    assert 'text="✨ Что сегодня"' in menu
    assert '"show_today": "Что сегодня"' in editor


def test_miniapp_recap_is_single_runtime_and_uses_live_intelligence() -> None:
    index = Path("app/static/miniapp/index.html").read_text(encoding="utf-8")
    js = Path("app/static/miniapp/engagement-layer.js").read_text(encoding="utf-8")
    css = Path("app/static/miniapp/engagement-layer.css").read_text(encoding="utf-8")
    assert index.count("engagement-layer.js") == 1
    assert index.count("engagement-layer.css") == 1
    assert "v0.18.1 · Phantom Recap" in index
    assert "/api/intelligence?days=7" in js
    assert "data-recap=\"today\"" in js
    assert "data-recap=\"week\"" in js
    assert "smart-stories" in js
    assert "function streak" in js
    assert "story-detail" in js
    assert "MutationObserver" in js
    assert "prefers-reduced-motion" in css
    assert ".smart-story" in css
