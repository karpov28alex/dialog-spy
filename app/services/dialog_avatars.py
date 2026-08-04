from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings

AVAILABLE = "available"
NO_PHOTO = "no_photo"
UNAVAILABLE = "unavailable"
RETRY = "retry"

_DOWNLOAD_SEMAPHORE = asyncio.Semaphore(2)
_ACTIVE: set[int] = set()


@dataclass(slots=True)
class AvatarState:
    dialog_id: int
    peer_telegram_id: int
    status: str
    storage_key: str | None
    next_retry_at: datetime | None


def avatar_path(settings: Settings, dialog_id: int) -> Path:
    return settings.media_root / "avatars" / f"dialog-{dialog_id}.jpg"


async def ensure_registry_row(session: AsyncSession, dialog_id: int, peer_id: int) -> None:
    await session.execute(
        text(
            """
            INSERT INTO dialog_avatars (dialog_id, peer_telegram_id, status)
            VALUES (:dialog_id, :peer_id, 'retry')
            ON CONFLICT (dialog_id) DO UPDATE
            SET peer_telegram_id = EXCLUDED.peer_telegram_id,
                updated_at = NOW()
            """
        ),
        {"dialog_id": dialog_id, "peer_id": peer_id},
    )


async def get_state(session: AsyncSession, dialog_id: int) -> AvatarState | None:
    row = (
        await session.execute(
            text(
                """
                SELECT dialog_id, peer_telegram_id, status, storage_key, next_retry_at
                FROM dialog_avatars
                WHERE dialog_id = :dialog_id
                """
            ),
            {"dialog_id": dialog_id},
        )
    ).mappings().first()
    return AvatarState(**row) if row else None


async def _resolve_file_id(bot: Bot, peer_id: int) -> tuple[str, str | None]:
    try:
        photos = await bot.get_user_profile_photos(peer_id, limit=1)
        if photos.photos:
            return AVAILABLE, photos.photos[0][-1].file_id
        chat = await bot.get_chat(peer_id)
        photo = getattr(chat, "photo", None)
        file_id = getattr(photo, "big_file_id", None) or getattr(photo, "small_file_id", None)
        return (AVAILABLE, file_id) if file_id else (NO_PHOTO, None)
    except TelegramRetryAfter:
        return RETRY, None
    except TelegramBadRequest as exc:
        message = str(exc).lower()
        if "user not found" in message or "chat not found" in message:
            return UNAVAILABLE, None
        return RETRY, None
    except Exception:
        return RETRY, None


async def refresh_avatar(
    session: AsyncSession,
    bot: Bot,
    settings: Settings,
    *,
    dialog_id: int,
    peer_id: int,
) -> str:
    await ensure_registry_row(session, dialog_id, peer_id)
    async with _DOWNLOAD_SEMAPHORE:
        status, file_id = await _resolve_file_id(bot, peer_id)
        now = datetime.now(UTC)
        attempts_sql = "attempts + 1"
        retry_at = None
        error = None
        storage_key = None

        if status == AVAILABLE and file_id:
            try:
                telegram_file = await bot.get_file(file_id)
                if not telegram_file.file_path:
                    raise RuntimeError("Telegram returned an empty file path")
                output = BytesIO()
                await bot.download_file(telegram_file.file_path, destination=output)
                payload = output.getvalue()
                if not payload:
                    raise RuntimeError("Telegram returned an empty avatar")
                path = avatar_path(settings, dialog_id)
                path.parent.mkdir(parents=True, exist_ok=True)
                temporary = path.with_suffix(f".tmp-{os.getpid()}")
                temporary.write_bytes(payload)
                temporary.replace(path)
                storage_key = str(path.relative_to(settings.media_root))
            except Exception as exc:
                status = RETRY
                retry_at = now + timedelta(minutes=15)
                error = f"{type(exc).__name__}: {exc}"
        elif status == RETRY:
            retry_at = now + timedelta(minutes=15)
        elif status == UNAVAILABLE:
            retry_at = now + timedelta(days=7)
        elif status == NO_PHOTO:
            retry_at = now + timedelta(days=1)

        await session.execute(
            text(
                f"""
                UPDATE dialog_avatars
                SET status = :status,
                    telegram_file_id = :file_id,
                    storage_key = COALESCE(:storage_key, storage_key),
                    attempts = {attempts_sql},
                    checked_at = :checked_at,
                    next_retry_at = :next_retry_at,
                    last_error = :last_error,
                    updated_at = NOW()
                WHERE dialog_id = :dialog_id
                """
            ),
            {
                "status": status,
                "file_id": file_id,
                "storage_key": storage_key,
                "checked_at": now,
                "next_retry_at": retry_at,
                "last_error": error,
                "dialog_id": dialog_id,
            },
        )
        return status


def should_schedule(state: AvatarState | None) -> bool:
    if state is None:
        return True
    if state.status == AVAILABLE and state.storage_key:
        return False
    return state.next_retry_at is None or state.next_retry_at <= datetime.now(UTC)


def mark_active(dialog_id: int) -> bool:
    if dialog_id in _ACTIVE:
        return False
    _ACTIVE.add(dialog_id)
    return True


def mark_finished(dialog_id: int) -> None:
    _ACTIVE.discard(dialog_id)
