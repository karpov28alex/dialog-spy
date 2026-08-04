from pathlib import Path


def test_miniapp_loads_product_experience_last() -> None:
    source = Path("app/static/miniapp/index.html").read_text(encoding="utf-8")
    assert "product-experience.css?v=0.16.0" in source
    assert "product-experience.js?v=0.16.0" in source
    assert source.index("product-experience.js") > source.index("archive-workspace.js")
    assert "v0.16.0 · Phantom Stories" in source


def test_product_experience_contains_stories_charts_and_logo_loader() -> None:
    js = Path("app/static/miniapp/product-experience.js").read_text(encoding="utf-8")
    css = Path("app/static/miniapp/product-experience.css").read_text(encoding="utf-8")
    assert "phantom:stories:seen" in js
    assert "px-chart-grid" in js
    assert "Персональный факт" in js
    assert "@keyframes px-blink" in css
    assert ".px-story-viewer" in css


def test_shareable_statistics_owns_current_callback() -> None:
    setup = Path("app/bot/setup.py").read_text(encoding="utf-8")
    handler = Path("app/bot/product_experience_handlers.py").read_text(encoding="utf-8")
    assert setup.index("product_experience_router") < setup.index("statistics_card_router)")
    assert 'F.data.in_({"user:stats", "product:stats"})' in handler
    assert "answer_photo" in handler
    assert "switch_inline_query" in handler


def test_access_funnel_uses_branded_success_presentation() -> None:
    setup = Path("app/bot/setup.py").read_text(encoding="utf-8")
    handler = Path("app/bot/product_experience_handlers.py").read_text(encoding="utf-8")
    assert "access_funnel_module.send_access_screen = branded_send_access_screen" in setup
    assert "Подключение управляется в настройках Telegram Business" in handler
    assert "activate_trial_after_channel" in handler
    assert "has_active_business" in handler


def test_dialog_export_is_telegram_style_html() -> None:
    route = Path("app/api/routes/dialog_export.py").read_text(encoding="utf-8")
    user_router = Path("app/api/routes/user.py").read_text(encoding="utf-8")
    assert '/export/dialogs/{dialog_id}.html' in route
    assert "Content-Disposition" in route
    assert "message out" not in route  # direction is selected dynamically
    assert '"out" if item.direction == "outgoing" else "in"' in route
    assert "router.include_router(dialog_export_router)" in user_router
