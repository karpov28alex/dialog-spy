from pathlib import Path


def test_profile_card_has_no_archive_activity_strip() -> None:
    source = Path("app/bot/profile_card_handlers.py").read_text(encoding="utf-8")
    assert "АКТИВНОСТЬ АРХИВА" not in source
    assert "engagement =" not in source
    assert "width, height = 1280, 680" in source
