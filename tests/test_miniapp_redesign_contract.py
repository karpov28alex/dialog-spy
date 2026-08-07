from pathlib import Path


def test_redesign_uses_one_runtime_and_mobile_styles() -> None:
    source = Path("app/static/miniapp/index.html").read_text(encoding="utf-8")
    css = Path("app/static/miniapp/phantom-redesign.css").read_text(encoding="utf-8")
    assert "/app/phantom-redesign.css?v=0.17.7" in source
    assert "/app/phantom-redesign.js" not in source
    assert source.count("product-experience.js") == 1
    assert source.count("global-search.js") == 1
    assert ".px-stories-shell" in css
    assert ".gs-launch" in css
    assert ".phantom-fab{display:none!important}" in css


def test_redesign_has_phone_breakpoints_and_light_palette() -> None:
    css = Path("app/static/miniapp/phantom-redesign.css").read_text(encoding="utf-8")
    assert "@media(max-width:390px)" in css
    assert "html[data-theme='light']" in css
    assert "body[data-theme='light']" in css
    assert "--ph-bg:#f4f0fb" in css
    assert "data:image" not in css
