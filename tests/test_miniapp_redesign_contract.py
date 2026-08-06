from pathlib import Path


def test_redesign_assets_are_loaded() -> None:
    source = Path("app/static/miniapp/index.html").read_text(encoding="utf-8")
    assert "/app/phantom-redesign.css?v=" in source
    assert "/app/phantom-redesign.js?v=" in source
    assert "Phantom Redesign" in source


def test_redesign_is_built_from_code_not_mockup_images() -> None:
    css = Path("app/static/miniapp/phantom-redesign.css").read_text(encoding="utf-8")
    js = Path("app/static/miniapp/phantom-redesign.js").read_text(encoding="utf-8")
    for marker in (
        ".phantom-stories",
        ".phantom-story-overlay",
        ".phantom-metric-grid",
        ".phantom-leader-row",
        ".phantom-fab",
    ):
        assert marker in css
    for marker in (
        "enhanceHome",
        "enhanceDialogs",
        "enhanceStats",
        "openStory",
        "installFab",
    ):
        assert marker in js
    assert "data:image" not in css
    assert "mockup" not in js.lower()
