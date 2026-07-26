from typing import Any

STANDARD_MEDIA_KEYS = (
    "video",
    "voice",
    "video_note",
    "document",
    "audio",
    "animation",
    "sticker",
)
IGNORED_FALLBACK_KEYS = {
    "thumbnail",
    "thumb",
    "cover",
    "photo",
    "live_photo",
    "paid_media",
    *STANDARD_MEDIA_KEYS,
}


def _add_candidate(
    output: list[dict],
    seen: set[str],
    kind: str,
    item: Any,
    path: str,
) -> None:
    if not isinstance(item, dict):
        return
    file_id = item.get("file_id")
    if not file_id or file_id in seen:
        return
    seen.add(file_id)
    output.append({"kind": kind, "item": item, "path": path})


def _add_largest_photo(
    output: list[dict], seen: set[str], photos: Any, kind: str, path: str
) -> None:
    if isinstance(photos, list) and photos:
        _add_candidate(output, seen, kind, photos[-1], path)


def _extract_live_photo(
    output: list[dict], seen: set[str], live_photo: Any, path: str
) -> None:
    if not isinstance(live_photo, dict):
        return
    _add_candidate(output, seen, "live_photo", live_photo, path)
    _add_largest_photo(
        output,
        seen,
        live_photo.get("photo"),
        "photo",
        f"{path}.photo[-1]",
    )


def _extract_paid_media(output: list[dict], seen: set[str], paid_info: Any) -> None:
    if not isinstance(paid_info, dict):
        return
    entries = paid_info.get("paid_media")
    if not isinstance(entries, list):
        return
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        media_type = entry.get("type")
        base = f"paid_media.paid_media.{index}"
        if media_type == "photo":
            _add_largest_photo(
                output, seen, entry.get("photo"), "paid_media", f"{base}.photo[-1]"
            )
        elif media_type == "video":
            _add_candidate(output, seen, "paid_media", entry.get("video"), f"{base}.video")
        elif media_type == "live_photo":
            live_photo = entry.get("live_photo")
            if isinstance(live_photo, dict):
                _add_candidate(output, seen, "paid_media", live_photo, f"{base}.live_photo")
                _add_largest_photo(
                    output,
                    seen,
                    live_photo.get("photo"),
                    "paid_media",
                    f"{base}.live_photo.photo[-1]",
                )


def extract_media(raw: dict) -> list[dict]:
    """Extract every primary downloadable media file, excluding thumbnails."""
    output: list[dict] = []
    seen: set[str] = set()

    _add_largest_photo(output, seen, raw.get("photo"), "photo", "photo[-1]")
    for key in STANDARD_MEDIA_KEYS:
        _add_candidate(output, seen, key, raw.get(key), key)
    _extract_live_photo(output, seen, raw.get("live_photo"), "live_photo")
    _extract_paid_media(output, seen, raw.get("paid_media"))

    # Future-proof fallback for unknown containers introduced by Telegram.
    def walk(value: Any, path: list[str]) -> None:
        if isinstance(value, dict):
            file_id = value.get("file_id")
            if file_id and file_id not in seen:
                _add_candidate(
                    output,
                    seen,
                    "protected_media",
                    value,
                    ".".join(path),
                )
            for key, nested in value.items():
                if key in IGNORED_FALLBACK_KEYS:
                    continue
                walk(nested, path + [key])
        elif isinstance(value, list):
            for index, nested in enumerate(value):
                walk(nested, path + [str(index)])

    walk(raw, [])
    return output


def storage_message_id(raw: dict) -> int | None:
    """Return a collision-resistant storage ID for regular or ephemeral messages."""
    normal = raw.get("message_id")
    if normal is not None:
        return int(normal)
    ephemeral = raw.get("ephemeral_message_id")
    if ephemeral is not None:
        return -(int(ephemeral) + 1)
    return None


def protected_reply_message(raw: dict) -> dict | None:
    """Return a replied protected message containing downloadable media.

    Telegram Business does not deliver view-once media as a standalone
    business_message in some clients. When the account owner replies to it
    before opening, Telegram embeds the original protected message in
    reply_to_message, including downloadable file_id values.
    """
    reply = raw.get("reply_to_message")
    if not isinstance(reply, dict):
        return None
    if not reply.get("has_protected_content"):
        return None
    if storage_message_id(reply) is None:
        return None
    if not extract_media(reply):
        return None
    return reply
