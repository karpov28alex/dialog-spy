from pathlib import Path


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_intelligence_builds_behavioral_signals() -> None:
    source = read("app/services/intelligence.py")
    for marker in ("recent_messages", "previous_messages", "weekly_change", "incoming_share", '"rising"', '"fading"', '"pace"', '"direction"'):
        assert marker in source
    assert '"signals": safe_signals' in source


def test_bot_insights_include_period_comparison_and_dialog_changes() -> None:
    source = read("app/services/dialog_insights.py")
    assert "weekly_change" in source
    assert "rising" in source
    assert "fading" in source
    assert "recent_deleted" in source
    assert "recent_edited" in source
    assert "incoming" in source and "outgoing" in source


def test_miniapp_renders_signal_stories_and_trend() -> None:
    source = read("app/static/miniapp/engagement-layer.js")
    assert "signalRows" in source
    assert "PHANTOM INSIGHTS" in source
    assert "pulse-trend" in source
    assert "/api/intelligence?days=14" in source
    css = read("app/static/miniapp/engagement-layer.css")
    assert ".pulse-trend.up" in css
    assert ".pulse-trend.down" in css
