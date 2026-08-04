from __future__ import annotations

import asyncio
import html
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select

from app.bot.setup import bot
from app.core.config import Settings, get_settings
from app.core.security import decode_token
from app.db.models import Dialog
from app.db.session import SessionLocal, get_session
from app.services.dialog_avatars import (
    AVAILABLE,
    avatar_path,
    ensure_registry_row,
    get_state,
    mark_active,
    mark_finished,
    refresh_avatar,
    should_schedule,
)

router = APIRouter(prefix="/api", tags=["user"])
_TASKS: set[asyncio.Task[None]] = set()


def _placeholder(name: str | None, *, pending: bool) -> Response:
    initials = "?"
    if name:
        parts = [part for part in name.strip().split() if part]
        initials = "".join(part[0].upper() for part in parts[:2]) or "?"
    label = html.escape(initials)
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="192" height="192" viewBox="0 0 192 192">'
        '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        '<stop stop-color="#9f43ff"/><stop offset="1" stop-color="#43206f"/>'
        '</linearGradient></defs><rect width="192" height="192" rx="96" fill="url(#g)"/>'
        f'<text x="96" y="112" text-anchor="middle" font-family="system-ui,sans-serif" '
        f'font-size="68" font-weight="800" fill="white">{label}</text></svg>'
    )
    headers = {"Cache-Control": "no-store" if pending else "private, max-age=3600"}
    if pending:
        headers["X-Avatar-Pending"] = "1"
    return Response(svg, media_type="image/svg+xml", headers=headers)


def _jpeg(path: Path, dialog_id: int) -> Response:
    stat = path.stat()
    return Response(
        path.read_bytes(),
        media_type="image/jpeg",
        headers={
            "Cache-Control": "private, max-age=86400, stale-while-revalidate=604800",
            "ETag": f'"avatar-{dialog_id}-{int(stat.st_mtime)}-{stat.st_size}"',
        },
    )


async def _background_refresh(
    dialog_id: int,
    peer_id: int,
    settings: Settings,
) -> None:
    try:
        async with SessionLocal() as session, session.begin():
            await refresh_avatar(
                session,
                bot,
                settings,
                dialog_id=dialog_id,
                peer_id=peer_id,
            )
    finally:
        mark_finished(dialog_id)


def _schedule(dialog_id: int, peer_id: int, settings: Settings) -> None:
    if not mark_active(dialog_id):
        return
    task = asyncio.create_task(_background_refresh(dialog_id, peer_id, settings))
    _TASKS.add(task)
    task.add_done_callback(_TASKS.discard)


@router.get("/avatar/{token}", include_in_schema=False)
async def dialog_avatar(
    token: str,
    session=Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    try:
        subject = decode_token(token, "dialog_avatar", settings)
        user_id_text, dialog_id_text = subject.split(":", 1)
        user_id, dialog_id = int(user_id_text), int(dialog_id_text)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=403, detail="Invalid avatar token") from exc

    dialog = await session.scalar(
        select(Dialog).where(Dialog.id == dialog_id, Dialog.owner_user_id == user_id)
    )
    if not dialog or not dialog.peer_telegram_id:
        return _placeholder(dialog.peer_name if dialog else None, pending=False)

    path = avatar_path(settings, dialog.id)
    if path.is_file() and path.stat().st_size > 0:
        return _jpeg(path, dialog.id)

    await ensure_registry_row(session, dialog.id, dialog.peer_telegram_id)
    state = await get_state(session, dialog.id)
    await session.commit()

    if state and state.status == AVAILABLE and state.storage_key:
        stored = settings.media_root / state.storage_key
        if stored.is_file() and stored.stat().st_size > 0:
            return _jpeg(stored, dialog.id)

    pending = should_schedule(state)
    if pending:
        _schedule(dialog.id, dialog.peer_telegram_id, settings)
    return _placeholder(dialog.peer_name or dialog.peer_username, pending=pending)
