from pathlib import Path


def test_avatar_loader_uses_persistent_bounded_fetch_queue() -> None:
    source = Path("app/static/miniapp/avatar-bootstrap.js").read_text(encoding="utf-8")
    assert "MAX_CONCURRENT = 3" in source
    assert "IntersectionObserver" in source
    assert "rootMargin: '700px 0px'" in source
    assert "await fetch(job.source" in source
    assert "const tasks = new Map()" in source
    assert "const objectUrls = new Map()" in source
    assert "const probe = new Image()" not in source
    assert "fetchPriority = 'high'" not in source


def test_visual_refresh_is_loaded_last() -> None:
    source = Path("app/static/miniapp/index.html").read_text(encoding="utf-8")
    visual = source.index("/app/visual-refresh.css?v=0.15.1")
    archive = source.index("/app/archive-workspace.css?v=0.15.1")
    assert visual > archive
    assert "v0.15.1 · Visual Refresh" in source


def test_visual_refresh_covers_core_screens() -> None:
    source = Path("app/static/miniapp/visual-refresh.css").read_text(encoding="utf-8")
    for selector in (
        ".navcard",
        ".dialog",
        ".avatar",
        ".msg",
        ".settings-card",
        ".profile-card",
        ".search",
    ):
        assert selector in source
    assert "prefers-reduced-motion" in source
