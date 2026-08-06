from pathlib import Path


def test_redesign_assets_are_loaded() -> None:
    source = Path("app/static/miniapp/index.html").read_text(encoding="utf-8")
    assert "/app/phantom-redesign.css?v=0.17.1" in source
    assert "/app/phantom-mobile-fixes.css?v=0.17.1" in source
    assert "/app/phantom-redesign.js?v=0.17.1" in source
    assert "Phantom Mobile" in source
    assert 'content="dark light"' in source


def test_redesign_reuses_existing_features_without_duplicates() -> None:
    css = Path("app/static/miniapp/phantom-redesign.css").read_text(encoding="utf-8")
    fixes = Path("app/static/miniapp/phantom-mobile-fixes.css").read_text(encoding="utf-8")
    js = Path("app/static/miniapp/phantom-redesign.js").read_text(encoding="utf-8")
    assert ".phantom-metric-grid" in css
    assert ".phantom-leader-row" in css
    assert "enhanceStats" in js
    assert "removeLegacyDuplicates" in js
    assert "enhanceHome" not in js
    assert "enhanceDialogs" not in js
    assert "installFab" not in js
    assert "html[data-theme=light]" in fixes
    assert ".phantom-stories,.phantom-archive-summary" in fixes
    assert ".phantom-fab" in fixes
    assert "data:image" not in css
    assert "mockup" not in js.lower()
