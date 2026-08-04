from pathlib import Path


def test_ordinary_message_delivery_contract() -> None:
    source = Path("app/api/routes/webhook.py").read_text(encoding="utf-8")
    ordinary = source.split("elif update.business_message:", 1)[1].split(
        "elif update.edited_business_message:", 1
    )[0]

    # Ordinary messages may trigger unrelated referral lifecycle notifications,
    # but must not enqueue a generic copy of the archived business message.
    assert "format_edit_notification(" not in ordinary
    assert "format_delete_notification(" not in ordinary
    assert 'idempotency_key=f"business-message:' not in ordinary
