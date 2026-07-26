from app.contracts import DeletedNotice, MessageProcessResult


def test_message_contract_fields():
    assert list(MessageProcessResult.__dataclass_fields__) == [
        "owner",
        "dialog",
        "message",
        "event",
        "media",
        "previous_text",
    ]


def test_deleted_notice_contract_fields():
    assert list(DeletedNotice.__dataclass_fields__) == [
        "owner",
        "dialog",
        "message",
        "telegram_message_id",
    ]
