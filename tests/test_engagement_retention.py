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


def test_daily_and_weekly_recap_are_nested_under_statistics() -> None:
    menu = Path("app/bot/enhanced_user_menu.py").read_text(encoding="utf-8")
    navigation = Path("app/bot/navigation_v019.py").read_text(encoding="utf-8")
    assert "✨ Что сегодня" not in menu
    assert "engagement:recap:1" in navigation
    assert "engagement:recap:7" in navigation


def test_miniapp_recap_is_single_runtime_and_uses_live_intelligence() -> None:
    index = Path("app/static/miniapp/index.html").read_text(encoding="utf-8")
    js = Path("app/static/miniapp/engagement-layer.js").read_text(encoding="utf-8")
    css = Path("app/static/miniapp/engagement-layer.css").read_text(encoding="utf-8")
    dialog_state = Path("app/static/miniapp/dialog-state.js").read_text(encoding="utf-8")
    assert index.count("engagement-layer.js") == 1
    assert index.count("engagement-layer.css") == 1
    assert "v0.19.5 · Insight Links" in index
    assert "/api/intelligence?days=14" in js
    assert "data-recap=\"today\"" in js
    assert "data-recap=\"week\"" in js
    assert "smart-stories" in js
    assert "function streak" in js
    assert "signalRows" in js
    assert "story-detail" in js
    assert "MutationObserver" in js
    assert "readCache" in js
    assert "data-insights-refresh" in js
    assert "phantom:focus-dialog" in js
    assert "consumeFocusedDialog" in dialog_state
    assert "button.click()" in dialog_state
    assert "prefers-reduced-motion" in css
    assert ".smart-story" in css
    assert "pulseShimmer" in css
