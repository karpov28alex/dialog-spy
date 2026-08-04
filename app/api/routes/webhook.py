import traceback
import uuid

import structlog
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Update
from fastapi import APIRouter, Header, HTTPException, Request
from redis.asyncio import Redis
from sqlalchemy import select

from app.bot.admin_handlers import router as admin_router
from app.bot.handlers import router as command_router
from app.bot.setup import bot, dispatcher
from app.business.events import format_delete_notification, format_edit_notification
from app.core.config import get_settings
from app.db.models import FailedUpdate, MessageVersion, User
from app.db.session import SessionLocal
from app.modules.events.context import EventContextService
from app.modules.media.queue import MediaQueueService
from app.services.access_funnel import get_funnel_config, notification_is_redacted
from app.services.queue import enqueue_job
from app.services.telegram_updates import (
    claim_update,
    delete_business_messages,
    edit_business_message,
    finish_update,
    save_business_message,
    update_kind,
    upsert_business_connection,
)
from app.services.users import qualify_referral

router = APIRouter(tags=["telegram"])
settings = get_settings()
logger = structlog.get_logger()
dispatcher.include_router(admin_router)
dispatcher.include_router(command_router)
redis = Redis.from_url(settings.redis_url, decode_responses=True)
context_service = EventContextService()
media_queue = MediaQueueService(redis, context_service)


def _paywall_markup(config) -> dict | None:
    if not config.payment_url.startswith("https://"):
        return None
    markup = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text=config.payment_button_text, url=config.payment_url)
        ]]
    )
    return markup.model_dump(mode="json", exclude_none=True)


def _redacted_edit(config, message) -> str:
    return (
        f"❗️ <b>{config.redacted_actor} изменил(а) сообщение</b>\n"
        f"🕓 <b>Отправлено:</b> {message.sent_at.strftime('%d.%m.%Y · %H:%M:%S')}\n\n"
        f"<b>Старое сообщение:</b>\n<blockquote>{config.redacted_content}</blockquote>\n\n"
        f"<b>Новое сообщение:</b>\n<blockquote>{config.redacted_content}</blockquote>\n\n"
        "Оформите доступ, чтобы увидеть полную историю изменения."
    )


def _redacted_delete(config, message) -> str:
    deleted_at = message.deleted_at or message.sent_at
    return (
        f"🗑 <b>{config.redacted_actor} удалил сообщение</b>\n"
        f"🕓 <b>Отправлено:</b> {message.sent_at.strftime('%d.%m.%Y · %H:%M:%S')}\n"
        f"🕓 <b>Удалено:</b> {deleted_at.strftime('%d.%m.%Y · %H:%M:%S')}\n\n"
        f"<b>Сохранённое содержимое:</b>\n<blockquote>{config.redacted_content}</blockquote>\n\n"
        "Оформите доступ, чтобы увидеть сохранённый текст."
    )


async def _queue_connection_notification(session, *, update_id: int, connection) -> None:
    user = await session.get(User, connection.owner_user_id)
    if user is None:
        return
    preferences = await context_service.ensure_preferences(session, user)
    if not preferences.notifications_enabled or not preferences.notify_connection:
        return
    text = (
        "✅ <b>Telegram Business подключён</b>\n\nPhantom начал сохранять поддерживаемые бизнес-диалоги."
        if connection.is_active
        else "⚠️ <b>Telegram Business отключён</b>\n\nНовые сообщения больше не сохраняются. Архив остаётся доступным."
    )
    await enqueue_job(
        session,
        redis,
        kind="send_text",
        payload={"telegram_id": user.telegram_id, "text": text},
        idempotency_key=f"connection:{update_id}:{int(connection.is_active)}",
    )


async def _process_update(session, update: Update, update_id: int) -> None:
    if update.business_connection:
        connection = await upsert_business_connection(session, update.business_connection)
        if connection:
            await _queue_connection_notification(session, update_id=update_id, connection=connection)
        return

    if update.business_message:
        await media_queue.persist_embedded_reply(session, update.business_message)
        message, created = await save_business_message(session, update.business_message)
        if message and created:
            await media_queue.queue_downloads(session, message)
            await media_queue.queue_protected_reply(session, message)
            context = await context_service.owner_context(session, message)
            if context:
                qualified_referrer = await qualify_referral(
                    session, referred_user_id=context.user.id
                )
                if qualified_referrer:
                    await enqueue_job(
                        session,
                        redis,
                        kind="send_text",
                        payload={
                            "telegram_id": qualified_referrer.telegram_id,
                            "text": "✅ <b>Друг выполнил условия</b>\n\nОн подключил Telegram Business и начал пользоваться Phantom. Вам начислен бонусный доступ.",
                        },
                        idempotency_key=(
                            f"referral-qualified:{qualified_referrer.id}:{context.user.id}"
                        ),
                    )
        return

    if update.edited_business_message:
        message, changed, _ = await edit_business_message(
            session, update.edited_business_message
        )
        if message and changed:
            context = await context_service.owner_context(session, message)
            preferences = context.preferences if context else None
            if context and preferences.notifications_enabled and preferences.notify_edits:
                versions = list(
                    (
                        await session.scalars(
                            select(MessageVersion)
                            .where(MessageVersion.message_id == message.id)
                            .order_by(MessageVersion.version_number)
                        )
                    ).all()
                )
                funnel = await get_funnel_config()
                redacted = notification_is_redacted(context.user, funnel)
                await enqueue_job(
                    session,
                    redis,
                    kind="send_text",
                    payload={
                        "telegram_id": context.user.telegram_id,
                        "text": _redacted_edit(funnel, message)
                        if redacted
                        else format_edit_notification(
                            dialog=context.dialog,
                            settings=preferences,
                            message=message,
                            versions=versions,
                        ),
                        "reply_markup": _paywall_markup(funnel) if redacted else None,
                    },
                    idempotency_key=f"edit:{update_id}:{message.id}",
                )
        return

    if update.deleted_business_messages:
        deleted = await delete_business_messages(session, update.deleted_business_messages)
        for index, message in enumerate(deleted):
            if message is None:
                continue
            context = await context_service.owner_context(session, message)
            preferences = context.preferences if context else None
            if context and preferences.notifications_enabled and preferences.notify_deletions:
                funnel = await get_funnel_config()
                redacted = notification_is_redacted(context.user, funnel)
                await enqueue_job(
                    session,
                    redis,
                    kind="send_text",
                    payload={
                        "telegram_id": context.user.telegram_id,
                        "text": _redacted_delete(funnel, message)
                        if redacted
                        else format_delete_notification(
                            dialog=context.dialog,
                            settings=preferences,
                            message=message,
                        ),
                        "reply_markup": _paywall_markup(funnel) if redacted else None,
                    },
                    idempotency_key=f"delete:{update_id}:{index}:{message.id}",
                )
        return

    await dispatcher.feed_update(bot, update)


async def _handle_webhook(
    secret: str,
    request: Request,
    x_telegram_bot_api_secret_token: str | None,
) -> dict[str, bool]:
    if (
        secret != settings.telegram_webhook_secret
        and x_telegram_bot_api_secret_token != settings.telegram_webhook_secret
    ):
        raise HTTPException(status_code=403, detail="Forbidden")

    payload = await request.json()
    correlation_id = request.headers.get("x-correlation-id") or uuid.uuid4().hex
    kind = update_kind(payload)
    update_id = payload.get("update_id")
    if not isinstance(update_id, int):
        raise HTTPException(status_code=400, detail="Invalid update")

    logger.info(
        "telegram_update_received",
        update_id=update_id,
        kind=kind,
        correlation_id=correlation_id,
    )

    try:
        update = Update.model_validate(payload, context={"bot": bot})
        async with SessionLocal() as session, session.begin():
            if not await claim_update(session, update_id, kind):
                logger.info("telegram_update_duplicate", update_id=update_id, kind=kind)
                return {"ok": True}
            await _process_update(session, update, update_id)
            await finish_update(session, update_id)

        logger.info(
            "telegram_update_processed",
            update_id=update_id,
            kind=kind,
            correlation_id=correlation_id,
        )
        return {"ok": True}
    except Exception as exc:
        logger.exception(
            "telegram_update_failed",
            update_id=update_id,
            kind=kind,
            correlation_id=correlation_id,
        )
        async with SessionLocal() as session, session.begin():
            session.add(
                FailedUpdate(
                    update_id=update_id,
                    update_type=kind,
                    payload=payload,
                    error=str(exc),
                    stack_trace=traceback.format_exc(),
                    attempts=1,
                    resolved=False,
                    correlation_id=correlation_id,
                )
            )
        return {"ok": True}


@router.post("/telegram/webhook/{secret}", status_code=200)
async def telegram_webhook(
    secret: str,
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, bool]:
    return await _handle_webhook(secret, request, x_telegram_bot_api_secret_token)


@router.post(
    "/api/telegram/webhook/{secret}", status_code=200, include_in_schema=False
)
async def legacy_telegram_webhook(
    secret: str,
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, bool]:
    return await _handle_webhook(secret, request, x_telegram_bot_api_secret_token)
