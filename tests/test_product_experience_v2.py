from pathlib import Path


def test_miniapp_loads_single_product_experience_runtime() -> None:
    source = Path("app/static/miniapp/index.html").read_text(encoding="utf-8")
    assert "/app/product-experience.css?v=0.18.0" in source
    assert "/app/product-experience.js?v=0.18.0" in source
    assert source.index("product-experience.js") > source.index("archive-workspace.js")
    assert "/app/phantom-redesign.css?v=0.18.0" in source
    assert "/app/phantom-redesign.js" not in source
    assert "/app/runtime-fixes.js?v=0.18.0" in source
    assert "/app/stats-motion.js?v=0.18.0" in source
    assert "/app/stats-motion.css?v=0.18.0" in source
    assert "/app/dialog-state.js?v=0.18.0" in source
    assert "/app/engagement-layer.js?v=0.18.0" in source
    assert "/app/engagement-layer.css?v=0.18.0" in source
    assert "v0.18.1 · Phantom Recap" in source
    assert 'name="color-scheme" content="dark light"' in source


def test_product_experience_contains_stories_charts_and_logo_loader() -> None:
    js = Path("app/static/miniapp/product-experience.js").read_text(encoding="utf-8")
    css = Path("app/static/miniapp/product-experience.css").read_text(encoding="utf-8")
    assert "phantom:stories:seen" in js
    assert "px-chart-grid" in js
    assert "Персональный факт" in js
    assert ".boot .logo" in css
    assert ".px-story-viewer" in css


def test_archive_primary_filters_use_server_metrics() -> None:
    runtime = Path("app/static/miniapp/runtime-fixes.js").read_text(encoding="utf-8")
    metrics = Path("app/static/miniapp/archive-metrics.js").read_text(encoding="utf-8")
    assert "archiveEdited" in runtime
    assert "archiveDeleted" in runtime
    assert "archiveMedia" in runtime
    assert "stopImmediatePropagation" in runtime
    assert "archive:metrics-ready" in runtime
    assert "archive:metrics-ready" in metrics


def test_statistics_has_motion_dashboard_layer() -> None:
    js = Path("app/static/miniapp/stats-motion.js").read_text(encoding="utf-8")
    css = Path("app/static/miniapp/stats-motion.css").read_text(encoding="utf-8")
    assert "animateNumber" in js
    assert "motion-activity-fill" in js
    assert "motion-day-fill" in js
    assert "motion-metric-grid" in js
    assert "IntersectionObserver" in js
    assert "setupScrollMotion" in js
    assert "--motion-shift" in css
    assert "@media(max-width:430px)" in css
    assert "grid-template-columns:1fr!important" in css
    assert "@keyframes motionBar" in css
    assert "@keyframes motionAura" in css
    assert "prefers-reduced-motion" in css
    assert 'html[data-theme="light"]' in css


def test_engagement_layer_has_daily_pulse_and_motion() -> None:
    js = Path("app/static/miniapp/engagement-layer.js").read_text(encoding="utf-8")
    css = Path("app/static/miniapp/engagement-layer.css").read_text(encoding="utf-8")
    assert "PHANTOM PULSE" in js
    assert "Сегодня в архиве" in js
    assert "animateCounts" in js
    assert "/api/intelligence?days=7" in js
    assert "--pulse-shift" in css
    assert "@keyframes pulseAmbient" in css
    assert "prefers-reduced-motion" in css
    assert 'html[data-theme="light"]' in css


def test_shareable_statistics_owns_current_callback() -> None:
    setup = Path("app/bot/setup.py").read_text(encoding="utf-8")
    handler = Path("app/bot/product_experience_handlers.py").read_text(encoding="utf-8")
    product_mount = "dispatcher.include_router(product_experience_router)"
    legacy_mount = "dispatcher.include_router(statistics_card_router)"
    assert setup.index(product_mount) < setup.index(legacy_mount)
    assert 'F.data.in_({"user:stats", "product:stats"})' in handler
    assert "answer_photo" in handler


def test_access_funnel_uses_branded_success_presentation() -> None:
    setup = Path("app/bot/setup.py").read_text(encoding="utf-8")
    handler = Path("app/bot/product_experience_handlers.py").read_text(encoding="utf-8")
    assert "access_funnel_module.send_access_screen = branded_send_access_screen" in setup
    assert "activate_trial_after_channel" in handler
    assert "has_active_business" in handler


def test_dialog_export_is_telegram_style_html() -> None:
    route = Path("app/api/routes/dialog_export.py").read_text(encoding="utf-8")
    user_router = Path("app/api/routes/user.py").read_text(encoding="utf-8")
    assert '/export/dialogs/{dialog_id}.html' in route
    assert "Content-Disposition" in route
    assert "message out" not in route
    assert '"out" if item.direction == "outgoing" else "in"' in route
    assert "router.include_router(dialog_export_router)" in user_router