from __future__ import annotations

from datetime import UTC, datetime

import structlog
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message as TgMessage
from redis.asyncio import Redis
from sqlalchemy import select

from app.bot.setup import bot
from app.core.config import get_settings
from app.db.models import BusinessConnection, Media, User
from app.db.session import SessionLocal
from app.services.queue import enqueue_job
from app.services.telegram_updates import edit_business_message, save_business_message
from app.services.users import register_or_update_user

router = Router(name="group-archive")
settings = get_settings()
logger = structlog.get_logger()
redis = Redis.from_url(settings.redis_url, decode_responses=True)
GROUP_TYPES = {"group", "supergroup"}


def _connection_id(chat_id: int) -> str:
    return f"group:{chat_id}"


def _is_group(message: TgMessage) -> bool:
    return str(message.chat.type) in GROUP_TYPES


async def _is_group_admin(message: TgMessage) -> bool:
    if not message.from_user:
        return False
    member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    status = getattr(member.status, "value", member.status)
    return str(status) in {"creator", "administrator"}


async def _queue_media(session, message) -> None:
    rows = list((await session.scalars(select(Media).where(Media.message_id == message.id))).all())
    for media in rows:
        if media.download_status == "downloaded":
            continue
        await enqueue_job(
            session,
            redis,
            kind="download_media",
            payload={"media_id": media.id},
            idempotency_key=f"media:{media.id}",
        )


async def _active_connection(session, chat_id: int) -> BusinessConnection | None:
    return await session.scalar(
        select(BusinessConnection).where(
            BusinessConnection.telegram_connection_id == _connection_id(chat_id),
            BusinessConnection.is_active.is_(True),
        )
    )


@router.message(Command("phantom_enable"), F.chat.type.in_(GROUP_TYPES))
async def enable_group_archive(message: TgMessage) -> None:
    if not message.from_user or not await _is_group_admin(message):
        await message.answer("Подключить групповой архив может только администратор группы.")
        return

    async with SessionLocal() as session, session.begin():
        owner = await session.scalar(select(User).where(User.telegram_id == message.from_user.id).with_for_update())
        if owner is None:
            owner, _ = await register_or_update_user(
                session,
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                language_code=message.from_user.language_code,
            )

        connection = await session.scalar(
            select(BusinessConnection)
            .where(BusinessConnection.telegram_connection_id == _connection_id(message.chat.id))
            .with_for_update()
        )
        now = datetime.now(UTC)
        rights = {
            "mode": "private_group_archive",
            "chat_id": message.chat.id,
            "chat_title": message.chat.title,
        }
        if connection is None:
            connection = BusinessConnection(
                owner_user_id=owner.id,
                telegram_connection_id=_connection_id(message.chat.id),
                business_user_id=owner.telegram_id,
                is_active=True,
                rights=rights,
                connected_at=now,
                last_activity_at=now,
            )
            session.add(connection)
        else:
            connection.owner_user_id = owner.id
            connection.business_user_id = owner.telegram_id
            connection.is_active = True
            connection.rights = rights
            connection.disconnected_at = None
            connection.last_activity_at = now

    await message.answer(
        "✅ <b>Групповой архив Phantom включён</b>\n\n"
        "Новые сообщения, изменения и медиа этой группы будут сохраняться в отдельном диалоге. "
        "Архив доступен только подключившему администратору.\n\n"
        "Важно: Telegram не передаёт ботам события удаления обычных групповых сообщений."
    )


@router.message(Command("phantom_disable"), F.chat.type.in_(GROUP_TYPES))
async def disable_group_archive(message: TgMessage) -> None:
    if not message.from_user or not await _is_group_admin(message):
        await message.answer("Отключить групповой архив может только администратор группы.")
        return
    async with SessionLocal() as session, session.begin():
        connection = await session.scalar(
            select(BusinessConnection)
            .where(BusinessConnection.telegram_connection_id == _connection_id(message.chat.id))
            .with_for_update()
        )
        if connection:
            connection.is_active = False
            connection.disconnected_at = datetime.now(UTC)
    await message.answer("Групповой архив Phantom отключён. Ранее сохранённая история останется доступной.")


@router.edited_message(F.chat.type.in_(GROUP_TYPES))
async def archive_group_edit(message: TgMessage) -> None:
    async with SessionLocal() as session, session.begin():
        connection = await _active_connection(session, message.chat.id)
        if connection is None:
            return
        event = message.model_copy(update={"business_connection_id": connection.telegram_connection_id})
        stored, changed, _ = await edit_business_message(session, event)
        if stored and changed:
            await _queue_media(session, stored)
            logger.info("group_message_edited", chat_id=message.chat.id, message_id=stored.id)


@router.message(F.chat.type.in_(GROUP_TYPES))
async def archive_group_message(message: TgMessage) -> None:
    if (message.text or "").startswith("/phantom_"):
        return
    async with SessionLocal() as session, session.begin():
        connection = await _active_connection(session, message.chat.id)
        if connection is None:
            return
        event = message.model_copy(update={"business_connection_id": connection.telegram_connection_id})
        stored, created = await save_business_message(session, event)
        if stored and created:
            await _queue_media(session, stored)
            logger.info("group_message_archived", chat_id=message.chat.id, message_id=stored.id)
