from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_start_sends_launch_button_and_separate_offer():
    source = (ROOT / "backend/app/services.py").read_text(encoding="utf-8")
    block = source[source.index("async def notify_start"):source.index("async def notify_event")]
    assert block.count("await bot.send_message(") == 2
    assert "reply_markup=app_keyboard()" in block
    assert "Оферта и конфиденциальность" in block


def test_text_business_messages_are_delivered_by_worker():
    telegram = (ROOT / "backend/app/telegram.py").read_text(encoding="utf-8")
    worker = (ROOT / "backend/app/worker.py").read_text(encoding="utf-8")
    services = (ROOT / "backend/app/services.py").read_text(encoding="utf-8")
    assert '"new_message"' in telegram
    assert 'kind=="new_message"' in worker
    assert "async def notify_new_message" in services
    assert "not is_own_outgoing" in telegram
