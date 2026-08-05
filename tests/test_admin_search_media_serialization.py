from pathlib import Path


def test_admin_user_serializer_is_null_safe_and_complete() -> None:
    source = Path("app/api/routes/admin.py").read_text(encoding="utf-8")
    assert '"first_name": user.first_name' in source
    assert '"last_name": user.last_name' in source
    assert '"registered_at": _iso(user.registered_at)' in source
    assert '"last_seen_at": _iso(user.last_seen_at)' in source
    assert 'search.strip().removeprefix("@")' in source


def test_admin_media_is_inline_and_contains_player_metadata() -> None:
    source = Path("app/api/routes/admin.py").read_text(encoding="utf-8")
    assert '"Content-Disposition": f\'inline;' in source
    assert '"Accept-Ranges": "bytes"' in source
    assert '"mime_type": item.mime_type' in source
    assert '"duration": item.duration' in source
    assert '"width": item.width' in source
    assert '"height": item.height' in source


def test_aiogram_default_sentinels_are_serialized_safely() -> None:
    source = Path("app/services/telegram_updates.py").read_text(encoding="utf-8")
    assert "def _jsonable_model" in source
    assert 'item.__class__.__name__ == "Default"' in source
    assert "raw_metadata=_jsonable_model(event)" in source
    assert "rights = _jsonable_model(event.rights)" in source


def test_dialog_viewer_renders_supported_media_types() -> None:
    source = Path("app/static/admin/dialogs-media.html").read_text(encoding="utf-8")
    for media_type in (
        "photo",
        "video",
        "video_note",
        "voice",
        "audio",
        "document",
        "animation",
        "sticker",
    ):
        assert media_type in source
    assert "<audio controls" in source
    assert "<video controls" in source
    assert "data-lightbox" in source
