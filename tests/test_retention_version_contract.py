from pathlib import Path


def test_recap_assets_use_contract_safe_cache_buster() -> None:
    source = Path("app/static/miniapp/index.html").read_text(encoding="utf-8")
    assert "v0.19.5 · Insight Links" in source
    assert "engagement-layer.js?v=0.19.5" in source
    assert "engagement-layer.css?v=0.19.5" in source
