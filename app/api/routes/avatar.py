from __future__ import annotations

import asyncio
import html
import os
import time
from io import BytesIO
from pathlib import Path

from aiogram.exceptions import TelegramAPIError
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select

from app.bot.setup import bot
from app.core.config import Settings, get_settings
from app.core.security import decode_token
from app.db.models import Dialog
from app.db.session import get_session

router = APIRouter(prefix="/api", tags=["user"])

_AVATAR_REFRESH_SECONDS = 24 * 60 * 60
_DOWNLOAD_SEMAPHORE = asyncio.Semaphore(2)
_REFRESH_TASKS: set[asyncio.Task[None]] = set()
_LOCKS: dict[int, asyncio.Lock] = {}


def _avatar_path(settings: Settings, dialog_id: int) -> Path:
    return settings.media_root / "avatars" / f"dialog-{dialog_id}.jpg"


def _lock_for(dialog_id: int) -> asyncio.Lock:
    lock = _LOCKS.get(dialog_id)
    if lock is None:
        lock = asyncio.Lock()
        _LOCKS[dialog_id] = lock
    return lock


def _placeholder(name: str | None) -> Response:
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
    return Response(
        svg,
        media_type="image/svg+xml",
        headers={"Cache-Control": "private, max-age=3600, stale-while-revalidate=86400"},
    )


async def _telegram_avatar_bytes(peer_id: int) -> bytes | None:
    async with _DOWNLOAD_SEMAPHORE:
        file_id: str | None = None
        try:
            photos = await bot.get_user_profile_photos(peer_id, limit=1)
            if photos.photos:
                file_id = photos.photos[0][-1].file_id
        except TelegramAPIError:
            pass

        if not file_id:
            try:
                chat = await bot.get_chat(peer_id)
                photo = getattr(chat, "photo", None)
                file_id = getattr(photo, "big_file_id", None) or getattr(photo, "small_file_id", None)
            except TelegramAPIError:
                return None

        if not file_id:
            return None

        try:
            tg_file = await bot.get_file(file_id)
            if not tg_file.file_path:
                return None
            output = BytesIO()
            await bot.download_file(tg_file.file_path, destination=output)
            payload = output.getvalue()
            return payload or None
        except TelegramAPIError:
            return None


async def _refresh_cache(dialog_id: int, peer_id: int, path: Path) -> None:
    async with _lock_for(dialog_id):
        payload = await _telegram_avatar_bytes(peer_id)
        if not payload:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(f".tmp-{os.getpid()}")
        temporary.write_bytes(payload)
        temporary.replace(path)


def _schedule_refresh(dialog_id: int, peer_id: int, path: Path) -> None:
    task = asyncio.create_task(_refresh_cache(dialog_id, peer_id, path))
    _REFRESH_TASKS.add(task)
    task.add_done_callback(_REFRESH_TASKS.discard)


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
        return _placeholder(dialog.peer_name if dialog else None)

    path = _avatar_path(settings, dialog.id)
    if path.is_file() and path.stat().st_size > 0:
        age = max(0, time.time() - path.stat().st_mtime)
        if age >= _AVATAR_REFRESH_SECONDS:
            _schedule_refresh(dialog.id, dialog.peer_telegram_id, path)
        return Response(
            path.read_bytes(),
            media_type="image/jpeg",
            headers={
                "Cache-Control": "private, max-age=86400, stale-while-revalidate=604800",
                "ETag": f'"avatar-{dialog.id}-{int(path.stat().st_mtime)}-{path.stat().st_size}"',
            },
        )

    await _refresh_cache(dialog.id, dialog.peer_telegram_id, path)
    if path.is_file() and path.stat().st_size > 0:
        return Response(
            path.read_bytes(),
            media_type="image/jpeg",
            headers={"Cache-Control": "private, max-age=86400, stale-while-revalidate=604800"},
        )

    return _placeholder(dialog.peer_name or dialog.peer_username)
