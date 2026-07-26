from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_version_contract():
    assert 'version="0.8.8"' in (ROOT / 'app/main.py').read_text()

def test_queue_contract():
    text = (ROOT / 'app/queue.py').read_text()
    assert 'QUEUE_KEY="dialogspy:jobs"' in text

def test_subscription_statuses():
    from app.models import SubscriptionStatus
    assert SubscriptionStatus.past_due.value == "past_due"


def test_dialog_api_returns_message_timeline():
    source=(ROOT / "app/api.py").read_text()
    assert '"messages": [' in source
    assert '"is_outgoing": message.from_user_id == user.telegram_id' in source
    assert '"versions": [' in source
    assert '"ephemeral_hint": media.is_ephemeral_hint' in source
