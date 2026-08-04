import structlog
from redis.asyncio import Redis
from sqlalchemy import select

from app.business.events import protected_reply_is_allowed
from app.db.models import BusinessConnection, Dialog, Media, Message, User
from app.modules.events.context import EventContextService
from app.services.queue import enqueue_job
from app.services.telegram_updates import save_business_message

logger = structlog.get_logger()


class MediaQueueService:
    def __init__(self, redis: Redis, context: EventContextService) -> None:
        self._redis = redis
        self._context = context

    async def queue_downloads(self, session, message: Message) -> list[Media]:
        rows = list(
            (await session.scalars(select(Media).where(Media.message_id == message.id))).all()
        )
        for media in rows:
            if media.download_status == "downloaded":
                continue
            await enqueue_job(
                session,
                self._redis,
                kind="download_media",
                payload={"media_id": media.id},
                idempotency_key=f"media:{media.id}",
            )
        return rows

    async def persist_embedded_reply(self, session, event) -> None:
        target = event.reply_to_message
        if target is None or not event.business_connection_id:
            return
        has_media = any(
            (
                target.photo,
                target.video,
                target.voice,
                target.video_note,
                target.document,
                target.animation,
                target.audio,
                target.sticker,
            )
        )
        if not has_media:
            return
        preferences = await self._context.preferences_for_connection(
            session, event.business_connection_id
        )
        if preferences is None or not preferences.save_protected_media:
            return
        connection = await session.scalar(
            select(BusinessConnection).where(
                BusinessConnection.telegram_connection_id == event.business_connection_id
            )
        )
        if connection is None:
            return
        existing = await session.scalar(
            select(Message).where(
                Message.business_connection_id == connection.id,
                Message.telegram_chat_id == target.chat.id,
                Message.telegram_message_id == target.message_id,
            )
        )
        if existing is not None:
            return
        target_with_connection = target.model_copy(
            update={"business_connection_id": event.business_connection_id}
        )
        stored, created = await save_business_message(session, target_with_connection)
        if not stored or not created:
            return
        metadata = dict(stored.raw_metadata or {})
        metadata["_capture_reason"] = "embedded_reply_missing_original"
        stored.raw_metadata = metadata
        media_rows = list(
            (await session.scalars(select(Media).where(Media.message_id == stored.id))).all()
        )
        for media in media_rows:
            media.is_protected = True
        await session.flush()
        await self.queue_downloads(session, stored)
        logger.info(
            "embedded_protected_reply_archived",
            message_id=stored.id,
            media_count=len(media_rows),
        )

    async def queue_protected_reply(self, session, reply_message: Message) -> None:
        if reply_message.reply_to_message_id is None:
            return
        context = await self._context.owner_context(session, reply_message)
        if context is None or not context.preferences.save_protected_media:
            return
        protected = await session.scalar(
            select(Media)
            .join(Message, Message.id == Media.message_id)
            .where(
                Message.business_connection_id == reply_message.business_connection_id,
                Message.telegram_chat_id == reply_message.telegram_chat_id,
                Message.telegram_message_id == reply_message.reply_to_message_id,
                Media.is_protected.is_(True),
            )
            .order_by(Media.id)
            .limit(1)
        )
        if protected is None:
            return
        decision = protected_reply_is_allowed(media=protected, reply_message=reply_message)
        if not decision.allowed:
            logger.warning(
                "protected_media_delivery_blocked",
                media_id=protected.id,
                message_id=reply_message.id,
                reason=decision.reason,
            )
            return
        preferences = context.preferences
        if not preferences.notifications_enabled or not preferences.notify_protected_media:
            return
        await enqueue_job(
            session,
            self._redis,
            kind="deliver_protected_media",
            payload={
                "media_id": protected.id,
                "owner_user_id": context.user.id,
                "dialog_name": context.dialog.peer_name or context.dialog.peer_username,
            },
            idempotency_key=f"protected-reply:{reply_message.id}:{protected.id}",
        )
