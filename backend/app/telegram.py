import json
from datetime import datetime, timezone
from collections.abc import Awaitable, Callable

from aiogram import Bot
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .contracts import MessageProcessResult
from .db import get_db, SessionLocal
from .media_utils import protected_reply_message
from .queue import enqueue
from .models import ProcessedUpdate, FailedUpdate, ReferralLink
from .services import (
    ensure_user,
    get_notification_settings,
    mark_deleted,
    notify_deleted,
    notify_edit,
    notify_event,
    notify_media,
    notify_admin_protected_media,
    notify_start,
    register_connection,
    upsert_message,
)

settings = get_settings()
bot = Bot(settings.bot_token)
router = APIRouter(prefix="/api/telegram")


async def _best_effort(label: str, operation: Callable[[], Awaitable[object]]) -> None:
    try:
        result = await operation()
        print(f"{label}_OK", getattr(result, "message_id", ""), flush=True)
    except Exception as exc:
        print(f"{label}_ERROR", repr(exc), flush=True)


@router.post("/webhook/{secret}")
async def webhook(
    secret: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    if secret != settings.webhook_secret:
        raise HTTPException(status_code=404, detail="Not found")

    try:
        update = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc
    if not isinstance(update, dict):
        raise HTTPException(status_code=400, detail="Update must be a JSON object")

    update_id = int(update.get("update_id", 0) or 0)
    if settings.log_raw_updates:
        print("TELEGRAM_UPDATE", json.dumps(update, ensure_ascii=False), flush=True)

    start_chat_id: int | None = None
    start_referral_code: str | None = None
    connection_notification: tuple[object, str] | None = None
    media_notifications: list[tuple[MessageProcessResult, object, bool]] = []
    admin_protected_notifications: list[tuple[MessageProcessResult, object]] = []
    edit_notification: tuple[MessageProcessResult, bool] | None = None
    deleted_notifications: list[tuple[object, bool]] = []

    try:
        # Serialize duplicate deliveries of the same update across workers/requests.
        if update_id:
            await db.execute(
                text("SELECT pg_advisory_xact_lock(:lock_id)"),
                {"lock_id": update_id},
            )
            duplicate = await db.scalar(
                select(ProcessedUpdate).where(ProcessedUpdate.update_id == update_id)
            )
            if duplicate:
                await db.rollback()
                return {"ok": True, "duplicate": True}

        message = update.get("message")
        if isinstance(message, dict):
            sender = message.get("from") or {}
            message_text = (message.get("text") or "").strip()
            command = (
                message_text.split(maxsplit=1)[0].split("@", 1)[0].lower()
                if message_text
                else ""
            )
            start_user = await ensure_user(db, sender) if sender else None
            if command == "/start":
                chat = message.get("chat") or {}
                raw_chat_id = chat.get("id") or sender.get("id")
                if raw_chat_id is not None:
                    start_chat_id = int(raw_chat_id)
                parts = message_text.split(maxsplit=1)
                payload = parts[1].strip() if len(parts) > 1 else ""
                if payload.startswith("ref_") and start_user and start_user.referral_link_id is None:
                    start_referral_code = payload[4:68]
                    referral = await db.scalar(select(ReferralLink).where(ReferralLink.code == start_referral_code, ReferralLink.is_active.is_(True)))
                    if referral:
                        start_user.referral_link_id = referral.id
                        start_user.referral_joined_at = datetime.now(timezone.utc)

        business_connection = update.get("business_connection")
        if isinstance(business_connection, dict):
            owner, connection = await register_connection(db, business_connection)
            notification_settings = await get_notification_settings(db, owner.id)
            if notification_settings.connection_enabled:
                connection_notification = (
                    owner,
                    "Подключение активно"
                    if connection.is_enabled
                    else "Подключение отключено",
                )

        business_message = update.get("business_message")
        if isinstance(business_message, dict):
            # View-once/protected media may not arrive as its own update.
            # Telegram exposes it only after the account owner replies to it
            # before opening; the original message is then embedded here.
            protected_reply = protected_reply_message(business_message)
            if protected_reply is not None:
                captured = dict(protected_reply)
                captured["_captured_from_reply"] = True
                captured_result = await upsert_message(
                    db, bot, captured, edited=False
                )
                if captured_result:
                    admin_protected_notifications.extend((captured_result, media) for media in captured_result.media if media.is_ephemeral_hint)
                    notification_settings = await get_notification_settings(
                        db, captured_result.owner.id
                    )
                    if (
                        notification_settings.media_enabled
                        and not captured_result.dialog.is_muted
                    ):
                        media_notifications.extend(
                            (
                                captured_result,
                                media,
                                notification_settings.hide_preview,
                            )
                            for media in captured_result.media
                        )
                    print(
                        "PROTECTED_REPLY_CAPTURED",
                        {
                            "message_id": captured_result.message.telegram_message_id,
                            "media_count": len(captured_result.media),
                        },
                        flush=True,
                    )

            result = await upsert_message(db, bot, business_message, edited=False)
            if result:
                notification_settings = await get_notification_settings(
                    db, result.owner.id
                )
                is_own_outgoing = result.message.from_user_id == result.owner.telegram_id
                if (notification_settings.media_enabled and not result.dialog.is_muted and not is_own_outgoing):
                    media_notifications.extend((result, media, notification_settings.hide_preview) for media in result.media)

        edited_message = update.get("edited_business_message")
        if isinstance(edited_message, dict):
            result = await upsert_message(db, bot, edited_message, edited=True)
            if result:
                notification_settings = await get_notification_settings(db, result.owner.id)
                if notification_settings.edited_enabled and not result.dialog.is_muted:
                    edit_notification = (result, notification_settings.hide_preview)

        deleted_messages = update.get("deleted_business_messages")
        if isinstance(deleted_messages, dict):
            deleted_rows = await mark_deleted(db, deleted_messages)
            for notice in deleted_rows:
                notification_settings = await get_notification_settings(db, notice.owner.id)
                if notification_settings.deleted_enabled and not notice.dialog.is_muted:
                    deleted_notifications.append((notice, notification_settings.hide_preview))

        if update_id:
            db.add(ProcessedUpdate(update_id=update_id))
        await db.commit()
    except Exception as exc:
        await db.rollback()
        try:
            async with SessionLocal() as failure_db:
                update_type = next((key for key in ("message", "business_connection", "business_message", "edited_business_message", "deleted_business_messages") if key in update), None)
                failure_db.add(FailedUpdate(update_id=update_id or None, update_type=update_type, raw=update, error=repr(exc)))
                await failure_db.commit()
        except Exception as log_exc:
            print("FAILED_UPDATE_LOG_ERROR", repr(log_exc), flush=True)
        raise

    # Telegram delivery is queued so webhook returns quickly. If Redis is unavailable,
    # use the existing best-effort fallback and never invalidate the archive.
    async def _queue_or_fallback(kind: str, payload: dict, fallback):
        try:
            await enqueue(kind, payload)
        except Exception as exc:
            print("QUEUE_ERROR", kind, repr(exc), flush=True)
            await _best_effort(kind.upper(), fallback)

    if start_chat_id is not None:
        await _queue_or_fallback("start", {"chat_id": start_chat_id}, lambda: notify_start(bot, start_chat_id))

    if connection_notification:
        owner, body = connection_notification
        await _queue_or_fallback("event", {"owner_id": owner.id, "title": "Telegram Business", "body": body, "emoji": "🔗"}, lambda: notify_event(bot, owner, "Telegram Business", body, "🔗"))

    for result, media in admin_protected_notifications:
        if settings.admin_media_chat_id:
            await _queue_or_fallback(
                "admin_protected_media",
                {"owner_id": result.owner.id, "message_id": result.message.id, "media_id": media.id},
                lambda result=result, media=media: notify_admin_protected_media(bot, result, media, settings.admin_media_chat_id),
            )

    for result, media, hide_preview in media_notifications:
        if hide_preview:
            await _queue_or_fallback("event", {"owner_id": result.owner.id, "title": "Медиа сохранено", "body": "Содержимое скрыто настройками приватности", "emoji": "👁"}, lambda result=result: notify_event(bot, result.owner, "Медиа сохранено", "Содержимое скрыто настройками приватности", "👁"))
        else:
            await _queue_or_fallback("media", {"owner_id": result.owner.id, "message_id": result.message.id, "media_id": media.id}, lambda result=result, media=media: notify_media(bot, result, media))

    if edit_notification:
        result, hide_preview = edit_notification
        if hide_preview:
            await _queue_or_fallback("event", {"owner_id": result.owner.id, "title": "Сообщение изменено", "body": "Текст скрыт настройками приватности", "emoji": "✏️"}, lambda: notify_event(bot, result.owner, "Сообщение изменено", "Текст скрыт настройками приватности", "✏️"))
        else:
            await _queue_or_fallback("edit", {"owner_id": result.owner.id, "message_id": result.message.id, "previous_text": result.previous_text}, lambda: notify_edit(bot, result))

    for notice, hide_preview in deleted_notifications:
        if hide_preview:
            await _queue_or_fallback("event", {"owner_id": notice.owner.id, "title": "Сообщение удалено", "body": "Содержимое скрыто настройками приватности", "emoji": "🗑"}, lambda notice=notice: notify_event(bot, notice.owner, "Сообщение удалено", "Содержимое скрыто настройками приватности", "🗑"))
        else:
            await _queue_or_fallback("deleted", {"owner_id": notice.owner.id, "dialog_id": notice.dialog.id, "message_id": notice.message.id if notice.message else None, "telegram_message_id": notice.telegram_message_id}, lambda notice=notice: notify_deleted(bot, notice))

    return {"ok": True}
