from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
from aiogram import Bot
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .contracts import DeletedNotice, MessageProcessResult
from .media_utils import extract_media, storage_message_id
from .models import (
    BusinessConnection,
    Dialog,
    Event,
    EventType,
    Message,
    MessageMedia,
    MessageVersion,
    NotificationSettings,
    SubscriptionStatus,
    User,
)

settings = get_settings()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def app_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="📱 Открыть Dialog Spy",
                web_app=WebAppInfo(url=settings.mini_app_url),
            )
        ]]
    )


async def ensure_user(db: AsyncSession, telegram_user: dict) -> User:
    telegram_id = int(telegram_user["id"])
    user = await db.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is None:
        user = User(
            telegram_id=telegram_id,
            username=telegram_user.get("username"),
            first_name=telegram_user.get("first_name"),
            last_name=telegram_user.get("last_name"),
            language_code=telegram_user.get("language_code"),
            subscription_status=SubscriptionStatus.trial,
            retention_days=settings.retention_days_default,
        )
        db.add(user)
        await db.flush()
        db.add(NotificationSettings(owner_id=user.id))
    else:
        user.username = telegram_user.get("username", user.username)
        user.first_name = telegram_user.get("first_name", user.first_name)
        user.last_name = telegram_user.get("last_name", user.last_name)
        user.language_code = telegram_user.get("language_code", user.language_code)
        notification_row = await db.scalar(
            select(NotificationSettings).where(NotificationSettings.owner_id == user.id)
        )
        if notification_row is None:
            db.add(NotificationSettings(owner_id=user.id))
    await db.flush()
    return user


async def ensure_dialog(
    db: AsyncSession,
    owner_id: int,
    connection_id: str,
    chat: dict,
) -> Dialog:
    chat_id = int(chat["id"])
    # A Telegram peer must map to exactly one archive dialog for an owner.
    # Business connection IDs can change after reconnects and must not split the chat.
    dialog = await db.scalar(
        select(Dialog).where(
            Dialog.owner_id == owner_id,
            Dialog.telegram_chat_id == chat_id,
        ).order_by(Dialog.id)
    )
    title = (
        chat.get("title")
        or chat.get("first_name")
        or chat.get("username")
        or str(chat_id)
    )
    if dialog is None:
        dialog = Dialog(
            owner_id=owner_id,
            connection_id=connection_id,
            telegram_chat_id=chat_id,
            title=title,
            username=chat.get("username"),
        )
        db.add(dialog)
        await db.flush()
    else:
        dialog.title = title
        dialog.username = chat.get("username", dialog.username)
        # Keep the latest active connection for diagnostics only.
        dialog.connection_id = connection_id
    dialog.last_event_at = utcnow()
    return dialog


async def download_media(bot: Bot, media: MessageMedia) -> None:
    if not media.telegram_file_id:
        return
    base = Path(settings.media_dir)
    base.mkdir(parents=True, exist_ok=True)
    telegram_file = await bot.get_file(media.telegram_file_id)
    suffix = Path(telegram_file.file_path or "").suffix or ".bin"
    target = base / f"{media.message_id}_{media.id}{suffix}"
    temporary = target.with_suffix(target.suffix + ".part")
    try:
        await bot.download_file(telegram_file.file_path, destination=temporary)
        temporary.replace(target)
        media.local_path = str(target)
    finally:
        temporary.unlink(missing_ok=True)


async def register_connection(db: AsyncSession, payload: dict):
    owner = await ensure_user(db, payload["user"])
    connection_id = payload["id"]
    connection = await db.scalar(
        select(BusinessConnection).where(
            BusinessConnection.connection_id == connection_id
        )
    )
    if connection is None:
        connection = BusinessConnection(
            connection_id=connection_id,
            owner_id=owner.id,
            business_user_id=int(payload["user"]["id"]),
        )
        db.add(connection)
    else:
        connection.owner_id = owner.id
        connection.business_user_id = int(payload["user"]["id"])
    connection.is_enabled = bool(payload.get("is_enabled", True))
    connection.rights = payload.get("rights") or {}

    if connection.is_enabled and owner.trial_started_at is None:
        owner.trial_started_at = utcnow()
        owner.trial_ends_at = utcnow() + timedelta(days=settings.trial_days)
        owner.subscription_status = SubscriptionStatus.trial

    event = Event(
        owner_id=owner.id,
        event_type=EventType.connection,
        title=(
            "Telegram Business подключён"
            if connection.is_enabled
            else "Telegram Business отключён"
        ),
        summary=connection_id,
        payload=payload,
    )
    db.add(event)
    await db.flush()
    return owner, connection


async def upsert_message(
    db: AsyncSession,
    bot: Bot,
    raw: dict,
    edited: bool = False,
) -> MessageProcessResult | None:
    connection_id = raw.get("business_connection_id")
    chat = raw.get("chat")
    telegram_message_id = storage_message_id(raw)
    if not connection_id or not isinstance(chat, dict) or telegram_message_id is None:
        return None

    connection = await db.scalar(
        select(BusinessConnection).where(
            BusinessConnection.connection_id == connection_id
        )
    )
    if connection is None or not connection.is_enabled:
        return None
    owner = await db.get(User, connection.owner_id)
    if owner is None or owner.is_blocked:
        return None

    dialog = await ensure_dialog(db, owner.id, connection_id, chat)
    if dialog.is_excluded:
        return None

    chat_id = int(chat["id"])
    message = await db.scalar(
        select(Message).where(
            Message.connection_id == connection_id,
            Message.telegram_chat_id == chat_id,
            Message.telegram_message_id == telegram_message_id,
        )
    )
    text = raw.get("text") or raw.get("caption")
    candidates = extract_media(raw)
    previous_text = message.current_text if message else None
    content_type = candidates[0]["kind"] if candidates else "text"

    if message is None:
        sender = raw.get("from") or {}
        message = Message(
            owner_id=owner.id,
            dialog_id=dialog.id,
            connection_id=connection_id,
            telegram_chat_id=chat_id,
            telegram_message_id=telegram_message_id,
            from_user_id=sender.get("id"),
            from_name=(
                " ".join(
                    filter(None, [sender.get("first_name"), sender.get("last_name")])
                )
                or sender.get("username")
            ),
            from_username=sender.get("username"),
            current_text=text,
            content_type=content_type,
            media_group_id=raw.get("media_group_id"),
            reply_to_message_id=(raw.get("reply_to_message") or {}).get("message_id"),
            sent_at=datetime.fromtimestamp(
                raw.get("date", int(utcnow().timestamp())), timezone.utc
            ),
            raw=raw,
        )
        db.add(message)
        await db.flush()
        db.add(MessageVersion(message_id=message.id, version_no=1, text=text, raw=raw))
        event_type = EventType.created
        title = "Новое сообщение"
    else:
        version_count = await db.scalar(
            select(func.count(MessageVersion.id)).where(
                MessageVersion.message_id == message.id
            )
        )
        changed = text != message.current_text
        if changed:
            db.add(
                MessageVersion(
                    message_id=message.id,
                    version_no=int(version_count or 0) + 1,
                    text=text,
                    raw=raw,
                )
            )
        message.current_text = text
        message.content_type = content_type
        message.raw = raw
        if edited:
            message.edited_at = utcnow()
        event_type = EventType.edited if edited else EventType.created
        title = "Сообщение изменено" if edited else "Сообщение получено"

    saved_media: list[MessageMedia] = []
    protected_hint = bool(
        raw.get("ephemeral_message_id") is not None
        or raw.get("has_protected_content")
        or raw.get("self_destruct_type")
        or raw.get("ttl_seconds")
    )
    for candidate in candidates:
        item = candidate["item"]
        unique_id = item.get("file_unique_id") or item.get("file_id")
        existing = None
        if unique_id:
            existing = await db.scalar(
                select(MessageMedia).where(
                    MessageMedia.message_id == message.id,
                    MessageMedia.telegram_file_unique_id == unique_id,
                )
            )
        if existing is not None:
            continue
        media = MessageMedia(
            message_id=message.id,
            media_type=candidate["kind"],
            telegram_file_id=item.get("file_id"),
            telegram_file_unique_id=unique_id,
            mime_type=item.get("mime_type"),
            file_size=item.get("file_size"),
            is_ephemeral_hint=protected_hint,
        )
        db.add(media)
        await db.flush()
        try:
            if not media.file_size or media.file_size <= settings.max_media_mb * 1024 * 1024:
                await download_media(bot, media)
            else:
                print(
                    "MEDIA_SKIPPED_TOO_LARGE",
                    candidate["path"],
                    media.file_size,
                    flush=True,
                )
        except Exception as exc:
            print("MEDIA_DOWNLOAD_ERROR", candidate["path"], repr(exc), flush=True)
        saved_media.append(media)

    event = Event(
        owner_id=owner.id,
        dialog_id=dialog.id,
        message_id=message.id,
        event_type=(EventType.media if saved_media and not edited else event_type),
        title=("Медиа сохранено" if saved_media and not edited else title),
        summary=(text[:500] if text else content_type),
        payload={
            "previous_text": previous_text,
            "media_count": len(saved_media),
            "protected_hint": protected_hint,
            "raw_keys": list(raw.keys()),
            "ephemeral_message_id": raw.get("ephemeral_message_id"),
            "receiver_user_id": (raw.get("receiver_user") or {}).get("id"),
            "captured_from_reply": bool(raw.get("_captured_from_reply")),
        },
    )
    db.add(event)
    await db.flush()
    return MessageProcessResult(
        owner=owner,
        dialog=dialog,
        message=message,
        event=event,
        media=saved_media,
        previous_text=previous_text,
    )


async def mark_deleted(db: AsyncSession, payload: dict):
    connection_id = payload.get("business_connection_id")
    chat = payload.get("chat") or {}
    if not connection_id or "id" not in chat:
        return []
    connection = await db.scalar(
        select(BusinessConnection).where(
            BusinessConnection.connection_id == connection_id
        )
    )
    if connection is None:
        return []
    owner = await db.get(User, connection.owner_id)
    if owner is None:
        return []
    dialog = await ensure_dialog(db, owner.id, connection_id, chat)
    notifications = []
    for telegram_message_id in payload.get("message_ids", []):
        message = await db.scalar(
            select(Message).where(
                Message.connection_id == connection_id,
                Message.telegram_chat_id == int(chat["id"]),
                Message.telegram_message_id == telegram_message_id,
            )
        )
        if message is None:
            db.add(
                Event(
                    owner_id=owner.id,
                    dialog_id=dialog.id,
                    event_type=EventType.deleted,
                    title="Сообщение удалено",
                    summary="Содержимое не было получено до удаления",
                    payload={"telegram_message_id": telegram_message_id, "missing": True},
                )
            )
            notifications.append(
                DeletedNotice(
                    owner=owner,
                    dialog=dialog,
                    message=None,
                    telegram_message_id=telegram_message_id,
                )
            )
            continue
        if not message.is_deleted:
            message.is_deleted = True
            message.deleted_at = utcnow()
            db.add(
                Event(
                    owner_id=owner.id,
                    dialog_id=message.dialog_id,
                    message_id=message.id,
                    event_type=EventType.deleted,
                    title="Сообщение удалено",
                    summary=message.current_text or message.content_type,
                    payload={"telegram_message_id": telegram_message_id},
                )
            )
            notifications.append(
                DeletedNotice(
                    owner=owner,
                    dialog=dialog,
                    message=message,
                    telegram_message_id=telegram_message_id,
                )
            )
    await db.flush()
    return notifications


async def get_notification_settings(
    db: AsyncSession, owner_id: int
) -> NotificationSettings:
    row = await db.scalar(
        select(NotificationSettings).where(NotificationSettings.owner_id == owner_id)
    )
    if row is None:
        row = NotificationSettings(owner_id=owner_id)
        db.add(row)
        await db.flush()
    return row


def _person_html(message: Message | None, dialog: Dialog) -> str:
    name = (message.from_name if message else None) or dialog.title or "Пользователь"
    username = (message.from_username if message else None) or dialog.username
    user_id = (message.from_user_id if message else None) or dialog.telegram_chat_id
    href = None
    if username:
        href = f"https://t.me/{username.lstrip('@')}"
    elif user_id:
        href = f"tg://user?id={int(user_id)}"
    linked_name = f'<a href="{href}"><b>{escape(name)}</b></a>' if href else f'<b>{escape(name)}</b>'
    suffix = f" (@{escape(username.lstrip('@'))})" if username else ""
    return f"👤 {linked_name}{suffix}"


def _moment(value: datetime | None) -> str:
    if not value:
        return "время неизвестно"
    try:
        local = value.astimezone()
    except Exception:
        local = value
    return local.strftime("%d.%m.%Y · %H:%M:%S")


async def notify_start(bot: Bot, chat_id: int):
    return await bot.send_message(
        chat_id,
        "👁 <b>Dialog Spy</b>\n\n"
        "Бот запущен. Подключите его через Telegram Business и откройте Mini App.\n\n"
        "🔐 Чтобы сохранить фото или видео на один просмотр: не открывайте его, ответьте на него любым сообщением и дождитесь подтверждения.",
        parse_mode="HTML",
        reply_markup=app_keyboard(),
    )


async def notify_event(bot: Bot, owner: User, title: str, body: str | None, emoji: str = "⚡"):
    return await bot.send_message(owner.telegram_id, f"{emoji} <b>{escape(title)}</b>\n\n{escape(body or 'Без текста')}", parse_mode="HTML", reply_markup=app_keyboard())


async def notify_edit(bot: Bot, result: MessageProcessResult, versions: list[MessageVersion] | None = None):
    rows = versions or []
    if not rows:
        old = result.previous_text or "Без текста"
        rows = [
            MessageVersion(version_no=1, text=old, created_at=result.message.sent_at or result.message.created_at),
            MessageVersion(version_no=2, text=result.message.current_text or "Без текста", created_at=result.message.edited_at or utcnow()),
        ]
    history = []
    for index, row in enumerate(rows, 1):
        label = "Текущая версия" if index == len(rows) else f"Версия {index}"
        history.append(
            f"<b>{label}</b>\n"
            f"🕓 {_moment(row.created_at)}\n"
            f"<blockquote>{escape(row.text or 'Без текста')}</blockquote>"
        )
    text = (
        "✏️ <b>СООБЩЕНИЕ ИЗМЕНЕНО</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"{_person_html(result.message, result.dialog)}\n"
        f"💬 Диалог: <b>{escape(result.dialog.title or 'Без названия')}</b>\n"
        f"🕓 {_moment(result.message.edited_at)}\n\n"
        + "\n\n".join(history)
        + "\n━━━━━━━━━━━━━━━━━━\nВсе версии сохранены в истории диалога."
    )
    return await bot.send_message(
        result.owner.telegram_id,
        text,
        parse_mode="HTML",
        reply_markup=app_keyboard(),
        disable_web_page_preview=True,
    )


async def notify_deleted(bot: Bot, notice: DeletedNotice):
    content = "Содержимое не было получено до удаления" if notice.message is None else (notice.message.current_text or notice.message.content_type)
    sent = notice.message.sent_at if notice.message else None
    deleted = notice.message.deleted_at if notice.message else utcnow()
    text=(
        "🗑 <b>СООБЩЕНИЕ УДАЛЕНО</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"{_person_html(notice.message, notice.dialog)}\n"
        f"🕓 Отправлено: {_moment(sent)}\n"
        f"🗑 Удалено: {_moment(deleted)}\n\n"
        f"<blockquote>{escape(content)}</blockquote>\n"
        "━━━━━━━━━━━━━━━━━━\nКопия осталась в архиве Dialog Spy."
    )
    return await bot.send_message(notice.owner.telegram_id,text,parse_mode="HTML",reply_markup=app_keyboard(),disable_web_page_preview=True)


async def notify_media(bot: Bot, result: MessageProcessResult, media: MessageMedia):
    if not media.local_path or not Path(media.local_path).exists(): return None
    protected=media.is_ephemeral_hint
    kind_names={"photo":"Фотография","video":"Видео","voice":"Голосовое сообщение","video_note":"Видеосообщение","animation":"GIF","audio":"Аудио","document":"Документ"}
    caption=(
      ("🔐 <b>ЗАЩИЩЁННОЕ МЕДИА СОХРАНЕНО</b>\n" if protected else "📥 <b>МЕДИА СОХРАНЕНО</b>\n")
      + "━━━━━━━━━━━━━━━━━━\n"
      + _person_html(result.message,result.dialog) + "\n"
      + f"🕓 {_moment(result.message.sent_at)}\n"
      + f"📎 {escape(kind_names.get(media.media_type,media.media_type))}\n"
      + ("🛡 Файл перехвачен через ответ до открытия.\n" if protected else "✅ Файл добавлен в архив диалога.\n")
      + "━━━━━━━━━━━━━━━━━━\nОткройте Mini App, чтобы посмотреть переписку целиком."
    )
    upload=FSInputFile(media.local_path)
    common={"caption":caption,"parse_mode":"HTML"}
    if media.media_type=="photo": return await bot.send_photo(result.owner.telegram_id,upload,**common)
    if media.media_type=="video": return await bot.send_video(result.owner.telegram_id,upload,supports_streaming=True,**common)
    if media.media_type=="voice": return await bot.send_voice(result.owner.telegram_id,upload,**common)
    if media.media_type=="video_note":
        sent=await bot.send_video_note(result.owner.telegram_id,upload);await bot.send_message(result.owner.telegram_id,caption,parse_mode="HTML",disable_web_page_preview=True);return sent
    if media.media_type=="animation": return await bot.send_animation(result.owner.telegram_id,upload,**common)
    if media.media_type=="audio": return await bot.send_audio(result.owner.telegram_id,upload,**common)
    return await bot.send_document(result.owner.telegram_id,upload,**common)



async def notify_admin_protected_media(bot: Bot, result: MessageProcessResult, media: MessageMedia, chat_id: int):
    """Send a detailed protected-media audit copy to the configured admin chat."""
    if not media.local_path or not Path(media.local_path).exists():
        return None
    kind_names = {
        "photo": "Фотография", "video": "Видео", "voice": "Голосовое сообщение",
        "video_note": "Видеосообщение", "animation": "GIF", "audio": "Аудио",
        "document": "Документ",
    }
    owner_name = " ".join(filter(None, [result.owner.first_name, result.owner.last_name])) or str(result.owner.telegram_id)
    sender_name = result.message.from_name or result.dialog.title or "Неизвестный пользователь"
    sender_username = f"@{result.message.from_username}" if result.message.from_username else "нет"
    caption = (
        "🔐 <b>ЗАЩИЩЁННОЕ МЕДИА — АДМИН-ЛОГ</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Владелец бота:</b> {escape(owner_name)}"
        + (f" (@{escape(result.owner.username)})" if result.owner.username else "") + "\n"
        f"🆔 <b>Telegram ID владельца:</b> <code>{result.owner.telegram_id}</code>\n"
        f"💬 <b>Диалог:</b> {escape(result.dialog.title or 'Без названия')}\n"
        f"📨 <b>Отправитель:</b> {escape(sender_name)}\n"
        f"🔗 <b>Username:</b> {escape(sender_username)}\n"
        f"🆔 <b>ID отправителя:</b> <code>{result.message.from_user_id or 'нет'}</code>\n"
        f"📎 <b>Тип:</b> {escape(kind_names.get(media.media_type, media.media_type))}\n"
        f"📦 <b>Размер:</b> {media.file_size or 0} байт\n"
        f"🕓 <b>Получено:</b> {_moment(result.message.sent_at)}\n"
        f"🧾 <b>Message ID:</b> <code>{result.message.telegram_message_id}</code>\n"
        f"🔌 <b>Business connection:</b> <code>{escape(result.message.connection_id)}</code>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Файл получен через ответ до открытия и сохранён в архиве."
    )
    upload = FSInputFile(media.local_path)
    common = {"caption": caption, "parse_mode": "HTML"}
    if media.media_type == "photo":
        return await bot.send_photo(chat_id, upload, **common)
    if media.media_type == "video":
        return await bot.send_video(chat_id, upload, supports_streaming=True, **common)
    if media.media_type == "voice":
        return await bot.send_voice(chat_id, upload, **common)
    if media.media_type == "video_note":
        sent = await bot.send_video_note(chat_id, upload)
        await bot.send_message(chat_id, caption, parse_mode="HTML")
        return sent
    if media.media_type == "animation":
        return await bot.send_animation(chat_id, upload, **common)
    if media.media_type == "audio":
        return await bot.send_audio(chat_id, upload, **common)
    return await bot.send_document(chat_id, upload, **common)
