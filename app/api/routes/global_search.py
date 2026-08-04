from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import desc, or_, select

from app.api.deps import CurrentUser, SessionDep
from app.db.models import Dialog, Media, Message, MessageVersion

router = APIRouter(prefix="/api/search", tags=["search"])


def _snippet(*values: str | None, limit: int = 220) -> str:
    text = next((value.strip() for value in values if value and value.strip()), "")
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


@router.get("")
async def global_search(
    user: CurrentUser,
    session: SessionDep,
    q: str = Query(min_length=2, max_length=160),
    limit: int = Query(40, ge=1, le=100),
) -> dict:
    term = q.strip()
    pattern = f"%{term}%"

    dialogs = list((await session.scalars(
        select(Dialog)
        .where(
            Dialog.owner_user_id == user.id,
            or_(Dialog.peer_name.ilike(pattern), Dialog.peer_username.ilike(pattern)),
        )
        .order_by(desc(Dialog.last_message_at), desc(Dialog.id))
        .limit(limit)
    )).all())

    message_rows = list((await session.execute(
        select(Message, Dialog)
        .join(Dialog, Dialog.id == Message.dialog_id)
        .where(
            Dialog.owner_user_id == user.id,
            or_(Message.text.ilike(pattern), Message.caption.ilike(pattern)),
        )
        .order_by(desc(Message.sent_at), desc(Message.id))
        .limit(limit)
    )).all())

    version_rows = list((await session.execute(
        select(MessageVersion, Message, Dialog)
        .join(Message, Message.id == MessageVersion.message_id)
        .join(Dialog, Dialog.id == Message.dialog_id)
        .where(
            Dialog.owner_user_id == user.id,
            or_(MessageVersion.text.ilike(pattern), MessageVersion.caption.ilike(pattern)),
        )
        .order_by(desc(MessageVersion.created_at), desc(MessageVersion.id))
        .limit(limit)
    )).all())

    media_rows = list((await session.execute(
        select(Media, Message, Dialog)
        .join(Message, Message.id == Media.message_id)
        .join(Dialog, Dialog.id == Message.dialog_id)
        .where(
            Dialog.owner_user_id == user.id,
            or_(Media.filename.ilike(pattern), Media.mime_type.ilike(pattern), Media.media_type.ilike(pattern)),
        )
        .order_by(desc(Media.created_at), desc(Media.id))
        .limit(limit)
    )).all())

    results: list[dict] = []
    seen: set[tuple[str, int]] = set()

    for dialog in dialogs:
        key = ("dialog", dialog.id)
        seen.add(key)
        results.append({
            "kind": "dialog",
            "dialog_id": dialog.id,
            "message_id": None,
            "title": dialog.peer_name or dialog.peer_username or "Диалог",
            "subtitle": f"@{dialog.peer_username}" if dialog.peer_username else "Диалог",
            "snippet": "Открыть переписку",
            "at": dialog.last_message_at,
            "media_type": None,
            "edited": False,
            "deleted": False,
        })

    for message, dialog in message_rows:
        key = ("message", message.id)
        if key in seen:
            continue
        seen.add(key)
        results.append({
            "kind": "message",
            "dialog_id": dialog.id,
            "message_id": message.id,
            "title": dialog.peer_name or dialog.peer_username or "Диалог",
            "subtitle": "Сообщение",
            "snippet": _snippet(message.text, message.caption),
            "at": message.sent_at,
            "media_type": None,
            "edited": message.edited_at is not None,
            "deleted": message.is_deleted,
        })

    for version, message, dialog in version_rows:
        key = ("version", version.id)
        if key in seen:
            continue
        seen.add(key)
        results.append({
            "kind": "version",
            "dialog_id": dialog.id,
            "message_id": message.id,
            "title": dialog.peer_name or dialog.peer_username or "Диалог",
            "subtitle": f"Версия {version.version_number}",
            "snippet": _snippet(version.text, version.caption),
            "at": version.created_at,
            "media_type": None,
            "edited": True,
            "deleted": message.is_deleted,
        })

    for media, message, dialog in media_rows:
        key = ("media", media.id)
        if key in seen:
            continue
        seen.add(key)
        results.append({
            "kind": "media",
            "dialog_id": dialog.id,
            "message_id": message.id,
            "title": dialog.peer_name or dialog.peer_username or "Диалог",
            "subtitle": media.filename or media.media_type,
            "snippet": _snippet(message.text, message.caption, media.mime_type, media.media_type),
            "at": message.sent_at,
            "media_type": media.media_type,
            "edited": message.edited_at is not None,
            "deleted": message.is_deleted,
        })

    results.sort(key=lambda item: item["at"] or 0, reverse=True)
    return {
        "query": term,
        "items": results[:limit],
        "counts": {
            "dialogs": len(dialogs),
            "messages": len(message_rows),
            "versions": len(version_rows),
            "media": len(media_rows),
        },
    }
