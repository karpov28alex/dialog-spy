from pathlib import Path


def test_loader_uses_locked_phantom_logo_without_spinner() -> None:
    html = Path("app/static/miniapp/index.html").read_text(encoding="utf-8")
    css = Path("app/static/miniapp/product-experience.css").read_text(encoding="utf-8")
    assert "phantom-logo.svg?v=0.16.1" in css
    assert '<div class="spinner">' not in html
    assert ".boot .spinner{display:none}" in css


def test_stories_do_not_require_telegram_business() -> None:
    source = Path("app/static/miniapp/product-experience.js").read_text(encoding="utf-8")
    assert "Telegram Business" not in source
    assert "Премиум не требуется" in source
    assert "настройки профиля" in source


def test_main_menu_statistics_opens_png_card_handler() -> None:
    source = Path("app/main.py").read_text(encoding="utf-8")
    assert 'text="📊 Статистика", callback_data="user:stats"' in source
    assert 'callback_data="intel:summary"' not in source
