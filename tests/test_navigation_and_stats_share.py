from pathlib import Path


def test_miniapp_uses_stable_navigation_layer() -> None:
    index = Path("app/static/miniapp/index.html").read_text(encoding="utf-8")
    script = Path("app/static/miniapp/navigation-stability.js").read_text(encoding="utf-8")
    app = Path("app/static/miniapp/app.js").read_text(encoding="utf-8")
    assert "/app/navigation-stability.js?v=0.17.6" in index
    assert "Navigation is owned by app.js" in script
    assert "window.location.assign" not in script
    assert "history[push?'pushState':'replaceState']" in app


def test_statistics_share_uses_cached_photo_and_referral_link() -> None:
    handler = Path("app/bot/statistics_share_inline.py").read_text(encoding="utf-8")
    setup = Path("app/bot/setup.py").read_text(encoding="utf-8")
    assert "InlineQueryResultCachedPhoto" in handler
    assert "phantom-statistics.png" in handler
    assert "?start=ref_" in handler
    assert "Посмотри, что расскажет твоя история общения" in handler
    assert "dispatcher.include_router(statistics_share_inline_router)" in setup
