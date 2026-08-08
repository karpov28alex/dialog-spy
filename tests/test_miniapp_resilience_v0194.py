from pathlib import Path


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_insights_retries_auth_and_falls_back_to_cache() -> None:
    source = read("app/static/miniapp/engagement-layer.js")
    assert "CACHE_KEY = 'phantom:intelligence:v0194'" in source
    assert "response.status === 401" in source
    assert "readCache()" in source
    assert "writeCache(data)" in source
    assert "render(fallback,{stale:true})" in source
    assert "REQUEST_TIMEOUT = 8000" in source


def test_insights_error_is_local_not_full_screen() -> None:
    source = read("app/static/miniapp/engagement-layer.js")
    assert "Phantom Insights временно недоступен" in source
    assert "Основные функции Mini App продолжают работать" in source
    assert "data-insights-refresh" in source
    css = read("app/static/miniapp/engagement-layer.css")
    assert ".pulse-skeleton-grid" in css
    assert "@keyframes pulseShimmer" in css


def test_behavior_signal_can_focus_its_dialog() -> None:
    insights = read("app/static/miniapp/engagement-layer.js")
    ui = read("app/static/miniapp/ui5.js")
    assert "item.dialog_id" in insights
    assert "phantom:focus-dialog" in insights
    assert "data-insight-dialog" in insights
    assert "sessionStorage.getItem('phantom:focus-dialog')" in ui
    assert "scrollIntoView" in ui
    assert "target.click()" in ui
