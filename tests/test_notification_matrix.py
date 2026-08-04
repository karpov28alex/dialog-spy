from pathlib import Path


def test_ordinary_message_delivery_contract() -> None:
    source = Path("app/api/routes/webhook.py").read_text(encoding="utf-8")

    # Ordinary messages may trigger media/referral workflows, but must not
    # enqueue a generic copy of the archived business message.
    assert "if update.business_message:" in source
    assert "await media_queue.queue_downloads(session, message)" in source
    assert "await media_queue.queue_protected_reply(session, message)" in source
    assert 'idempotency_key=f"business-message:' not in source
