from pathlib import Path


def test_share_card_contains_referral_call_to_action() -> None:
    source = Path("app/bot/engagement_handlers.py").read_text(encoding="utf-8")
    assert "Получить свою статистику" in source
    assert "?start=ref_" in source
    assert "Хочешь увидеть, кто чаще пишет, удаляет и меняет сообщения у тебя?" in source
    assert "engagement:share:" in source


def test_recap_supports_daily_weekly_and_streak() -> None:
    source = Path("app/bot/engagement_handlers.py").read_text(encoding="utf-8")
    assert "async def _recap" in source
    assert "def _streak" in source
    assert "days=1" in source
    assert "days=7" in source
    assert "дней подряд" in source
