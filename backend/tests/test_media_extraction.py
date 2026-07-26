from app.media_utils import extract_media


def test_photo_uses_only_largest_size():
    raw = {
        "photo": [
            {"file_id": "small", "file_unique_id": "s"},
            {"file_id": "large", "file_unique_id": "l"},
        ]
    }
    items = extract_media(raw)
    assert [(item["kind"], item["item"]["file_id"]) for item in items] == [
        ("photo", "large")
    ]


def test_video_thumbnail_and_cover_are_not_saved_separately():
    raw = {
        "video": {
            "file_id": "video-file",
            "file_unique_id": "video-unique",
            "thumbnail": {"file_id": "thumb-file", "file_unique_id": "thumb-unique"},
            "cover": [{"file_id": "cover-file", "file_unique_id": "cover-unique"}],
        }
    }
    items = extract_media(raw)
    assert [item["item"]["file_id"] for item in items] == ["video-file"]


def test_paid_photo_uses_largest_size():
    raw = {
        "paid_media": {
            "star_count": 10,
            "paid_media": [
                {
                    "type": "photo",
                    "photo": [
                        {"file_id": "paid-small", "file_unique_id": "ps"},
                        {"file_id": "paid-large", "file_unique_id": "pl"},
                    ],
                }
            ],
        }
    }
    items = extract_media(raw)
    assert [(item["kind"], item["item"]["file_id"]) for item in items] == [
        ("paid_media", "paid-large")
    ]


def test_live_photo_saves_video_and_largest_static_photo():
    raw = {
        "live_photo": {
            "file_id": "live-video",
            "file_unique_id": "lv",
            "photo": [
                {"file_id": "live-small", "file_unique_id": "ls"},
                {"file_id": "live-large", "file_unique_id": "ll"},
            ],
        }
    }
    items = extract_media(raw)
    assert [(item["kind"], item["item"]["file_id"]) for item in items] == [
        ("live_photo", "live-video"),
        ("photo", "live-large"),
    ]


def test_ephemeral_message_id_uses_separate_negative_namespace():
    from app.media_utils import storage_message_id

    assert storage_message_id({"message_id": 42, "ephemeral_message_id": 7}) == 42
    assert storage_message_id({"ephemeral_message_id": 7}) == -8
    assert storage_message_id({}) is None


def test_protected_reply_message_extracts_view_once_photo():
    from app.media_utils import protected_reply_message

    raw = {
        "message_id": 101,
        "text": "test",
        "reply_to_message": {
            "business_connection_id": "connection",
            "message_id": 100,
            "chat": {"id": 55, "type": "private"},
            "has_protected_content": True,
            "photo": [
                {"file_id": "small", "file_unique_id": "small-u"},
                {"file_id": "large", "file_unique_id": "large-u"},
            ],
        },
    }

    reply = protected_reply_message(raw)
    assert reply is not None
    assert reply["message_id"] == 100
    assert extract_media(reply)[0]["item"]["file_id"] == "large"


def test_unprotected_reply_is_not_treated_as_view_once_capture():
    from app.media_utils import protected_reply_message

    raw = {
        "reply_to_message": {
            "message_id": 100,
            "photo": [{"file_id": "large", "file_unique_id": "large-u"}],
        }
    }
    assert protected_reply_message(raw) is None
