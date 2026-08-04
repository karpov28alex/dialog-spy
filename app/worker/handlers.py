from datetime import UTC, datetime
from typing import Awaitable, Callable

from aiogram import Bot
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup

from app.business.events import is_protected_message
from app.core.config import Settings
from app.db.models import Job, Media, Message, User
from app.db.session import SessionLocal
from app.services.access import has_access
from app.services.access_funnel import get_funnel_config
from app.services.broadcasts import send_broadcast
from app.services.media import download_telegram_file, safe_media_path

JobHandler = Callable[[Job], Awaitable[None]]


class WorkerHandlers:
    def __init__(self, bot: Bot, settings: Settings) -> None:
        self._bot = bot
        self._settings = settings
        self._handlers: dict[str, JobHandler] = {
            "send_text": self.send_text,
            "broadcast_send": self.broadcast,
            "download_media": self.download_media,
            "send_protected_media": self.deliver_protected_media,
            "deliver_protected_media": self.deliver_protected_media,
        }

    async def handle(self, job: Job) -> None:
        handler = self._handlers.get(job.kind)
        if handler is None:
            raise RuntimeError(f"Unknown job kind: {job.kind}")
        await handler(job)

    async def send_text(self, job: Job) -> None:
        reply_markup = None
        raw_markup = job.payload.get("reply_markup")
        if raw_markup:
            reply_markup = InlineKeyboardMarkup.model_validate(raw_markup)
        await self._bot.send_message(
            job.payload["telegram_id"],
            job.payload["text"],
            reply_markup=reply_markup,
        )

    async def broadcast(self, job: Job) -> None:
        await send_broadcast(self._bot, job.payload)

    async def download_media(self, job: Job) -> None:
        async with SessionLocal() as session, session.begin():
            media = await session.get(
                Media,
                int(job.payload["media_id"]),
                with_for_update=True,
            )
            if not media or media.download_status == "downloaded":
                return
            await self._download(media)

    async def _download(self, media: Media) -> Media:
        storage_key = f"messages/{media.message_id}/{media.id}"
        checksum, size = await download_telegram_file(
            self._bot,
            media.telegram_file_id,
            storage_key,
            self._settings,
        )
        media.storage_key = storage_key
        media.checksum = checksum
        media.size = media.size or size
        media.download_status = "downloaded"
        media.downloaded_at = datetime.now(UTC)
        return media

    async def _ensure_protected_media_downloaded(self, media_id: int) -> Media:
        async with SessionLocal() as session, session.begin():
            media = await session.get(Media, media_id, with_for_update=True)
            if not media:
                raise RuntimeError("Media not found")
            message = await session.get(Message, media.message_id)
            if not message:
                raise RuntimeError("Media message not found")

            raw = message.raw_metadata or {}
            stored_message = type(
                "StoredTelegramMessage",
                (),
                {
                    "has_protected_content": raw.get("has_protected_content", False),
                    "model_dump": lambda self, **kwargs: raw,
                },
            )()
            decision = is_protected_message(stored_message)
            embedded_capture = raw.get("_capture_reason") == "embedded_reply_missing_original"
            if media.is_protected is not True or not (decision.allowed or embedded_capture):
                media.is_protected = False
                raise RuntimeError(
                    "Protected media invariant failed: no Telegram protection signal"
                )
            if media.download_status == "downloaded" and media.storage_key:
                return media
            return await self._download(media)

    @staticmethod
    def _payment_markup(url: str, text: str) -> InlineKeyboardMarkup | None:
        if not url.startswith("https://"):
            return None
        return InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=text, url=url)]]
        )

    async def deliver_protected_media(self, job: Job) -> None:
        owner_user_id = int(job.payload["owner_user_id"])
        async with SessionLocal() as session:
            user = await session.get(User, owner_user_id)
            if not user:
                raise RuntimeError("Owner not found")
            funnel = await get_funnel_config()
            if funnel.enabled and funnel.redact_expired_notifications and not has_access(user):
                await self._bot.send_message(
                    user.telegram_id,
                    "🔐 <b>Получено скрытое медиа</b>\n\n"
                    f"💬 <b>Диалог:</b> {funnel.redacted_actor}\n"
                    f"📎 <b>Содержимое:</b> {funnel.redacted_content}\n\n"
                    "Оформите доступ, чтобы получить сохранённый файл.",
                    reply_markup=self._payment_markup(
                        funnel.payment_url,
                        funnel.payment_button_text,
                    ),
                )
                return

        media = await self._ensure_protected_media_downloaded(
            int(job.payload["media_id"])
        )
        async with SessionLocal() as session:
            user = await session.get(User, owner_user_id)
            if not user:
                raise RuntimeError("Owner not found")
            await self._send_protected_file(user, media, job)

    async def _send_protected_file(self, user: User, media: Media, job: Job) -> None:
        if not media.storage_key:
            raise RuntimeError("Downloaded media has no storage key")
        path = safe_media_path(self._settings, media.storage_key)
        caption = (
            "🔐 <b>Скрытое медиа сохранено</b>\n\n"
            f"💬 <b>Диалог:</b> {job.payload.get('dialog_name') or 'Без имени'}\n"
            f"📎 <b>Тип:</b> {media.media_type}\n\n"
            "Медиа сохранено после вашего ответа на одноразовое сообщение. "
            "Его можно переслать или сохранить."
        )
        file = FSInputFile(path, filename=media.filename or f"protected-{media.id}")
        telegram_id = user.telegram_id
        if media.media_type == "photo":
            await self._bot.send_photo(telegram_id, photo=file, caption=caption, protect_content=False)
        elif media.media_type in {"video", "animation"}:
            await self._bot.send_video(telegram_id, video=file, caption=caption, protect_content=False)
        elif media.media_type == "voice":
            await self._bot.send_voice(telegram_id, voice=file, caption=caption, protect_content=False)
        elif media.media_type == "video_note":
            await self._bot.send_video_note(telegram_id, video_note=file, protect_content=False)
            await self._bot.send_message(telegram_id, caption)
        elif media.media_type == "audio":
            await self._bot.send_audio(telegram_id, audio=file, caption=caption, protect_content=False)
        elif media.media_type == "sticker":
            await self._bot.send_sticker(telegram_id, sticker=file, protect_content=False)
            await self._bot.send_message(telegram_id, caption)
        else:
            await self._bot.send_document(
                telegram_id,
                document=file,
                caption=caption,
                protect_content=False,
            )
