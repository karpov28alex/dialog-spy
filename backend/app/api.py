from datetime import datetime, timedelta, timezone
from pathlib import Path
import os

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from aiogram import Bot

from .db import get_db
from .deps import current_admin, current_user
from .models import (
    Admin,
    BusinessConnection,
    Dialog,
    Event,
    EventType,
    Message,
    MessageMedia,
    MessageVersion,
    NotificationSettings,
    SubscriptionStatus,
    User, Payment, PromoCode, FailedUpdate, AdminAudit, BackgroundJob, ReferralLink,
)
from .security import create_token, decode_token, validate_init_data, verify_password
from .config import get_settings
from .services import ensure_user

router = APIRouter(prefix="/api")
settings = get_settings()
profile_bot = Bot(settings.bot_token)


class TelegramAuth(BaseModel):
    init_data: str = ""


class AdminLogin(BaseModel):
    email: str
    password: str


class VipGrant(BaseModel):
    days: int = Field(default=30, ge=1, le=3650)

class ReferralLinkCreate(BaseModel):
    source: str = Field(min_length=1, max_length=255)
    campaign: str | None = Field(default=None, max_length=255)
    placement: str | None = Field(default=None, max_length=255)
    spend_rub: float = Field(default=0, ge=0, le=1_000_000_000)
    notes: str | None = Field(default=None, max_length=4000)


class DialogPatch(BaseModel):
    muted: bool | None = None
    excluded: bool | None = None


class SettingsPatch(BaseModel):
    deleted_enabled: bool | None = None
    edited_enabled: bool | None = None
    media_enabled: bool | None = None
    connection_enabled: bool | None = None
    hide_preview: bool | None = None
    digest_mode: str | None = None
    retention_days: int | None = Field(default=None, ge=1, le=3650)


@router.get("/health")
async def health():
    return {"ok": True, "version": "0.8.8"}


@router.post("/auth/telegram")
async def auth(data: TelegramAuth, db: AsyncSession = Depends(get_db)):
    user = await ensure_user(db, validate_init_data(data.init_data))
    await db.commit()
    return {
        "token": create_token(str(user.id), "user"),
        "user": {
            "id": user.id,
            "telegram_id": user.telegram_id,
            "first_name": user.first_name,
            "username": user.username,
        },
    }


@router.get("/me")
async def me(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    connection_count = await db.scalar(
        select(func.count(BusinessConnection.id)).where(
            BusinessConnection.owner_id == user.id,
            BusinessConnection.is_enabled.is_(True),
        )
    )
    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "name": " ".join(filter(None, [user.first_name, user.last_name])),
        "username": user.username,
        "subscription_status": user.subscription_status,
        "trial_ends_at": user.trial_ends_at,
        "vip_ends_at": user.vip_ends_at,
        "retention_days": user.retention_days,
        "business_connected": bool(connection_count),
    }


@router.get("/events")
async def events(
    type: EventType | None = None,
    dialog_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Event).where(Event.owner_id == user.id)
    if type:
        query = query.where(Event.event_type == type)
    if dialog_id:
        query = query.where(Event.dialog_id == dialog_id)
    rows = (
        await db.scalars(query.order_by(desc(Event.created_at)).limit(limit).offset(offset))
    ).all()
    return [
        {
            "id": event.id,
            "type": event.event_type,
            "title": event.title,
            "summary": event.summary,
            "dialog_id": event.dialog_id,
            "message_id": event.message_id,
            "created_at": event.created_at,
        }
        for event in rows
    ]


@router.get("/events/{event_id}")
async def event_detail(
    event_id: int,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    event = await db.scalar(
        select(Event).where(Event.id == event_id, Event.owner_id == user.id)
    )
    if event is None:
        raise HTTPException(404, "Event not found")
    message = await db.get(Message, event.message_id) if event.message_id else None
    versions = []
    media = []
    if message:
        versions = (
            await db.scalars(
                select(MessageVersion)
                .where(MessageVersion.message_id == message.id)
                .order_by(MessageVersion.version_no)
            )
        ).all()
        media = (
            await db.scalars(
                select(MessageMedia).where(MessageMedia.message_id == message.id)
            )
        ).all()
    return {
        "event": {
            "id": event.id,
            "type": event.event_type,
            "title": event.title,
            "summary": event.summary,
            "created_at": event.created_at,
            "payload": event.payload,
        },
        "message": None
        if not message
        else {
            "id": message.id,
            "from_name": message.from_name,
            "from_username": message.from_username,
            "text": message.current_text,
            "content_type": message.content_type,
            "sent_at": message.sent_at,
            "edited_at": message.edited_at,
            "deleted_at": message.deleted_at,
        },
        "versions": [
            {"version_no": row.version_no, "text": row.text, "created_at": row.created_at}
            for row in versions
        ],
        "media": [
            {
                "id": row.id,
                "type": row.media_type,
                "mime_type": row.mime_type,
                "file_size": row.file_size,
                "available": bool(row.local_path),
                "ephemeral_hint": row.is_ephemeral_hint,
            }
            for row in media
        ],
    }


@router.get("/dialogs")
async def dialogs(
    include_excluded: bool = False,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    # One SQL query instead of 2 extra queries per dialog. This is critical for
    # fast Mini App startup when an account has hundreds of chats.
    message_count = (
        select(func.count(Message.id))
        .where(Message.dialog_id == Dialog.id, Message.owner_id == user.id)
        .correlate(Dialog)
        .scalar_subquery()
    )
    deleted_count = (
        select(func.count(Message.id))
        .where(Message.dialog_id == Dialog.id, Message.owner_id == user.id, Message.is_deleted.is_(True))
        .correlate(Dialog)
        .scalar_subquery()
    )
    media_count = (
        select(func.count(MessageMedia.id))
        .join(Message, Message.id == MessageMedia.message_id)
        .where(Message.dialog_id == Dialog.id, Message.owner_id == user.id)
        .correlate(Dialog)
        .scalar_subquery()
    )
    def latest(column):
        return (
            select(column)
            .where(Message.dialog_id == Dialog.id, Message.owner_id == user.id)
            .order_by(desc(Message.sent_at), desc(Message.id))
            .limit(1)
            .correlate(Dialog)
            .scalar_subquery()
        )
    query = select(
        Dialog,
        message_count.label("message_count"),
        deleted_count.label("deleted_count"),
        media_count.label("media_count"),
        latest(Message.current_text).label("last_text"),
        latest(Message.content_type).label("last_content_type"),
        latest(Message.is_deleted).label("last_deleted"),
        latest(Message.from_user_id).label("last_from_user_id"),
        latest(Message.sent_at).label("last_sent_at"),
    ).where(Dialog.owner_id == user.id)
    if not include_excluded:
        query = query.where(Dialog.is_excluded.is_(False))
    rows = (await db.execute(query.order_by(desc(Dialog.last_event_at), desc(Dialog.id)))).all()
    return [
        {
            "id": dialog.id,
            "telegram_chat_id": dialog.telegram_chat_id,
            "title": dialog.title,
            "username": dialog.username,
            "messages": int(message_count or 0),
            "deleted": int(deleted_count or 0),
            "media": int(media_count or 0),
            "muted": dialog.is_muted,
            "excluded": dialog.is_excluded,
            "last_event_at": dialog.last_event_at,
            "last_message": None if last_sent_at is None else {
                "text": last_text,
                "content_type": last_content_type,
                "is_deleted": bool(last_deleted),
                "is_outgoing": last_from_user_id == user.telegram_id,
                "sent_at": last_sent_at,
            },
        }
        for dialog, message_count, deleted_count, media_count, last_text,
            last_content_type, last_deleted, last_from_user_id, last_sent_at in rows
    ]


@router.get("/dialogs/{dialog_id}/avatar")
async def dialog_avatar(
    dialog_id: int,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    dialog = await db.scalar(
        select(Dialog).where(Dialog.id == dialog_id, Dialog.owner_id == user.id)
    )
    if dialog is None:
        raise HTTPException(404, "Dialog not found")

    cache_dir = Path(settings.media_dir) / "avatars"
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / f"{user.id}_{dialog.telegram_chat_id}.jpg"
    if not target.exists():
        try:
            photos = await profile_bot.get_user_profile_photos(
                user_id=dialog.telegram_chat_id, limit=1
            )
            if not photos.photos:
                raise HTTPException(404, "Avatar not available")
            photo = photos.photos[0][-1]
            telegram_file = await profile_bot.get_file(photo.file_id)
            temporary = target.with_suffix(".part")
            try:
                await profile_bot.download_file(telegram_file.file_path, destination=temporary)
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
        except HTTPException:
            raise
        except Exception as exc:
            print("AVATAR_DOWNLOAD_ERROR", dialog.telegram_chat_id, repr(exc), flush=True)
            raise HTTPException(404, "Avatar not available") from exc
    return FileResponse(target, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=86400"})


@router.get("/dialogs/{dialog_id}")
async def dialog_detail(
    dialog_id: int,
    limit: int = Query(default=300, ge=1, le=500),
    before_id: int | None = None,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    dialog = await db.scalar(
        select(Dialog).where(Dialog.id == dialog_id, Dialog.owner_id == user.id)
    )
    if dialog is None:
        raise HTTPException(404, "Dialog not found")

    query = select(Message).where(
        Message.dialog_id == dialog.id,
        Message.owner_id == user.id,
    )
    if before_id is not None:
        query = query.where(Message.id < before_id)
    messages = (
        await db.scalars(
            query.order_by(desc(Message.sent_at), desc(Message.id)).limit(limit)
        )
    ).all()
    messages = list(reversed(messages))

    message_ids = [m.id for m in messages]
    media_map: dict[int, list[MessageMedia]] = {}
    versions_map: dict[int, list[MessageVersion]] = {}
    if message_ids:
        media_rows = (
            await db.scalars(
                select(MessageMedia)
                .where(MessageMedia.message_id.in_(message_ids))
                .order_by(MessageMedia.id)
            )
        ).all()
        for row in media_rows:
            media_map.setdefault(row.message_id, []).append(row)

        version_rows = (
            await db.scalars(
                select(MessageVersion)
                .where(MessageVersion.message_id.in_(message_ids))
                .order_by(MessageVersion.message_id, MessageVersion.version_no)
            )
        ).all()
        for row in version_rows:
            versions_map.setdefault(row.message_id, []).append(row)

    return {
        "dialog": {
            "id": dialog.id,
            "telegram_chat_id": dialog.telegram_chat_id,
            "title": dialog.title,
            "username": dialog.username,
            "muted": dialog.is_muted,
            "excluded": dialog.is_excluded,
            "last_event_at": dialog.last_event_at,
        },
        "messages": [
            {
                "id": message.id,
                "telegram_message_id": message.telegram_message_id,
                "from_name": message.from_name,
                "from_username": message.from_username,
                "is_outgoing": message.from_user_id == user.telegram_id,
                "text": message.current_text,
                "content_type": message.content_type,
                "reply_to_message_id": message.reply_to_message_id,
                "is_deleted": message.is_deleted,
                "sent_at": message.sent_at,
                "edited_at": message.edited_at,
                "deleted_at": message.deleted_at,
                "media": [
                    {
                        "id": media.id,
                        "type": media.media_type,
                        "mime_type": media.mime_type,
                        "file_size": media.file_size,
                        "available": bool(media.local_path),
                        "ephemeral_hint": media.is_ephemeral_hint,
                    }
                    for media in media_map.get(message.id, [])
                ],
                "versions": [
                    {
                        "version_no": version.version_no,
                        "text": version.text,
                        "created_at": version.created_at,
                    }
                    for version in versions_map.get(message.id, [])
                ],
            }
            for message in messages
        ],
        "has_more": len(messages) == limit,
    }


@router.patch("/dialogs/{dialog_id}")
async def patch_dialog(
    dialog_id: int,
    data: DialogPatch,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    dialog = await db.scalar(
        select(Dialog).where(Dialog.id == dialog_id, Dialog.owner_id == user.id)
    )
    if dialog is None:
        raise HTTPException(404, "Dialog not found")
    if data.muted is not None:
        dialog.is_muted = data.muted
    if data.excluded is not None:
        dialog.is_excluded = data.excluded
    await db.commit()
    return {"ok": True}


@router.get("/media")
async def media(
    kind: str | None = None,
    limit: int = Query(default=100, ge=1, le=200),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(MessageMedia, Message, Dialog)
        .join(Message, Message.id == MessageMedia.message_id)
        .join(Dialog, Dialog.id == Message.dialog_id)
        .where(Message.owner_id == user.id)
    )
    if kind:
        query = query.where(MessageMedia.media_type == kind)
    rows = (await db.execute(query.order_by(desc(MessageMedia.created_at)).limit(limit))).all()
    return [
        {
            "id": item.id,
            "type": item.media_type,
            "available": bool(item.local_path),
            "file_size": item.file_size,
            "created_at": item.created_at,
            "dialog_id": dialog.id,
            "dialog_title": dialog.title,
            "message_id": message.id,
        }
        for item, message, dialog in rows
    ]


@router.get("/media/{media_id}/download")
async def download(
    media_id: int,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    row = (
        await db.execute(
            select(MessageMedia, Message)
            .join(Message, Message.id == MessageMedia.message_id)
            .where(MessageMedia.id == media_id, Message.owner_id == user.id)
        )
    ).first()
    if row is None:
        raise HTTPException(404, "Media not found")
    media_row, _ = row
    if not media_row.local_path or not Path(media_row.local_path).exists():
        raise HTTPException(404, "File unavailable")
    return FileResponse(
        media_row.local_path,
        filename=Path(media_row.local_path).name,
        media_type=media_row.mime_type or "application/octet-stream",
    )




def _temporary_media_url(media_id: int, owner_id: int | None, admin: bool = False) -> str:
    subject = f"admin-media:{media_id}" if admin else f"user-media:{owner_id}:{media_id}"
    token = create_token(subject, "media_link", minutes=5)
    return f"/api/media/{media_id}/open?token={token}"

@router.get("/media/{media_id}/link")
async def media_link(media_id: int, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    exists = await db.scalar(select(MessageMedia.id).join(Message, Message.id == MessageMedia.message_id).where(MessageMedia.id == media_id, Message.owner_id == user.id))
    if exists is None: raise HTTPException(404, "Media not found")
    return {"url": _temporary_media_url(media_id, user.id)}

@router.get("/media/{media_id}/open")
async def media_open(media_id: int, token: str, db: AsyncSession = Depends(get_db)):
    payload = decode_token(token)
    if payload.get("role") != "media_link": raise HTTPException(401, "Invalid media link")
    subject = str(payload.get("sub", "")); media = await db.get(MessageMedia, media_id)
    if media is None or not media.local_path: raise HTTPException(404, "Media not found")
    message = await db.get(Message, media.message_id)
    allowed = subject == f"admin-media:{media_id}" or (message is not None and subject == f"user-media:{message.owner_id}:{media_id}")
    if not allowed: raise HTTPException(403, "Media link does not match file")
    path = Path(media.local_path)
    if not path.exists(): raise HTTPException(404, "File unavailable")
    mime = media.mime_type or "application/octet-stream"
    inline_types = {"photo", "video", "video_note", "voice", "audio", "animation"}
    disposition = "inline" if media.media_type in inline_types or mime == "application/pdf" else "attachment"
    return FileResponse(
        path,
        filename=path.name,
        media_type=mime,
        content_disposition_type=disposition,
        headers={"Cache-Control": "private, no-store"},
    )

@router.get("/admin/media/{media_id}/link")
async def admin_media_link(media_id: int, _: Admin = Depends(current_admin), db: AsyncSession = Depends(get_db)):
    media = await db.get(MessageMedia, media_id)
    if media is None: raise HTTPException(404, "Медиафайл не найден")
    return {"url": _temporary_media_url(media_id, None, admin=True)}

@router.get("/stats")
async def stats(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    data = {
        event_type.value: await db.scalar(
            select(func.count(Event.id)).where(
                Event.owner_id == user.id,
                Event.event_type == event_type,
            )
        )
        for event_type in EventType
    }
    data["dialogs"] = await db.scalar(
        select(func.count(Dialog.id)).where(Dialog.owner_id == user.id)
    )
    data["media"] = await db.scalar(
        select(func.count(MessageMedia.id))
        .join(Message, Message.id == MessageMedia.message_id)
        .where(Message.owner_id == user.id)
    )
    return data


@router.get("/settings")
async def get_settings(
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    settings = await db.scalar(
        select(NotificationSettings).where(NotificationSettings.owner_id == user.id)
    )
    if settings is None:
        settings = NotificationSettings(owner_id=user.id)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return {
        "deleted_enabled": settings.deleted_enabled,
        "edited_enabled": settings.edited_enabled,
        "media_enabled": settings.media_enabled,
        "connection_enabled": settings.connection_enabled,
        "hide_preview": settings.hide_preview,
        "digest_mode": settings.digest_mode,
        "retention_days": user.retention_days,
    }


@router.patch("/settings")
async def patch_settings(
    data: SettingsPatch,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    settings = await db.scalar(
        select(NotificationSettings).where(NotificationSettings.owner_id == user.id)
    )
    if settings is None:
        settings = NotificationSettings(owner_id=user.id)
        db.add(settings)
        await db.flush()
    for key in (
        "deleted_enabled",
        "edited_enabled",
        "media_enabled",
        "connection_enabled",
        "hide_preview",
        "digest_mode",
    ):
        value = getattr(data, key)
        if value is not None:
            setattr(settings, key, value)
    if data.retention_days is not None:
        user.retention_days = data.retention_days
    await db.commit()
    return {"ok": True}


@router.post("/admin/login")
async def admin_login(data: AdminLogin, db: AsyncSession = Depends(get_db)):
    admin = await db.scalar(select(Admin).where(Admin.email == data.email))
    if admin is None or not verify_password(data.password, admin.password_hash):
        raise HTTPException(401, "Invalid credentials")
    return {"token": create_token(str(admin.id), "admin")}


@router.get("/admin/overview")
async def overview(
    _: Admin = Depends(current_admin), db: AsyncSession = Depends(get_db)
):
    return {
        "users": await db.scalar(select(func.count(User.id))),
        "connections": await db.scalar(
            select(func.count(BusinessConnection.id)).where(
                BusinessConnection.is_enabled.is_(True)
            )
        ),
        "events": await db.scalar(select(func.count(Event.id))),
        "messages": await db.scalar(select(func.count(Message.id))),
        "media": await db.scalar(select(func.count(MessageMedia.id))),
        "active_vip": await db.scalar(
            select(func.count(User.id)).where(
                User.subscription_status == SubscriptionStatus.active
            )
        ),
    }


@router.get("/admin/users")
async def admin_users(
    _: Admin = Depends(current_admin), db: AsyncSession = Depends(get_db)
):
    rows = (
        await db.scalars(select(User).order_by(desc(User.created_at)).limit(300))
    ).all()
    return [
        {
            "id": user.id,
            "telegram_id": user.telegram_id,
            "name": user.first_name,
            "username": user.username,
            "status": user.subscription_status,
            "trial_ends_at": user.trial_ends_at,
            "vip_ends_at": user.vip_ends_at,
            "created_at": user.created_at,
            "blocked": user.is_blocked,
        }
        for user in rows
    ]


@router.get("/admin/users/{user_id}")
async def admin_user_detail(
    user_id: int,
    _: Admin = Depends(current_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "Пользователь не найден")
    connections = (await db.scalars(select(BusinessConnection).where(BusinessConnection.owner_id == user.id).order_by(desc(BusinessConnection.updated_at)))).all()
    dialogs_count = int((await db.scalar(select(func.count(Dialog.id)).where(Dialog.owner_id == user.id))) or 0)
    messages_count = int((await db.scalar(select(func.count(Message.id)).where(Message.owner_id == user.id))) or 0)
    deleted_count = int((await db.scalar(select(func.count(Message.id)).where(Message.owner_id == user.id, Message.is_deleted.is_(True)))) or 0)
    edited_count = int((await db.scalar(select(func.count(Message.id)).where(Message.owner_id == user.id, Message.edited_at.is_not(None)))) or 0)
    media_count = int((await db.scalar(select(func.count(MessageMedia.id)).join(Message, Message.id == MessageMedia.message_id).where(Message.owner_id == user.id))) or 0)
    protected_count = int((await db.scalar(select(func.count(MessageMedia.id)).join(Message, Message.id == MessageMedia.message_id).where(Message.owner_id == user.id, MessageMedia.is_ephemeral_hint.is_(True)))) or 0)
    storage_bytes = int((await db.scalar(select(func.coalesce(func.sum(MessageMedia.file_size), 0)).join(Message, Message.id == MessageMedia.message_id).where(Message.owner_id == user.id))) or 0)
    payments = (await db.scalars(select(Payment).where(Payment.owner_id == user.id).order_by(desc(Payment.created_at)).limit(50))).all()
    recent_dialogs = (await db.scalars(select(Dialog).where(Dialog.owner_id == user.id).order_by(desc(Dialog.last_event_at)).limit(20))).all()
    return {
        "user": {"id": user.id, "telegram_id": user.telegram_id, "name": user.first_name, "username": user.username, "status": user.subscription_status, "trial_ends_at": user.trial_ends_at, "vip_ends_at": user.vip_ends_at, "created_at": user.created_at, "blocked": user.is_blocked},
        "statistics": {"dialogs": dialogs_count, "messages": messages_count, "deleted": deleted_count, "edited": edited_count, "media": media_count, "protected_media": protected_count, "storage_bytes": storage_bytes},
        "connections": [{"id": c.id, "business_connection_id": c.connection_id, "enabled": c.is_enabled, "connected_at": c.connected_at, "updated_at": c.updated_at} for c in connections],
        "payments": [{"id": p.id, "amount_minor": p.amount_minor, "currency": p.currency, "status": p.status, "recurring": p.is_recurring, "created_at": p.created_at} for p in payments],
        "dialogs": [{"id": d.id, "title": d.title, "username": d.username, "muted": d.is_muted, "hidden": d.is_excluded, "last_event_at": d.last_event_at} for d in recent_dialogs],
    }


@router.get("/admin/events")
async def admin_events(
    _: Admin = Depends(current_admin), db: AsyncSession = Depends(get_db)
):
    rows = (
        await db.scalars(select(Event).order_by(desc(Event.created_at)).limit(300))
    ).all()
    return [
        {
            "id": event.id,
            "owner_id": event.owner_id,
            "type": event.event_type,
            "title": event.title,
            "summary": event.summary,
            "created_at": event.created_at,
        }
        for event in rows
    ]


@router.post("/admin/users/{user_id}/vip")
async def vip(
    user_id: int,
    data: VipGrant,
    admin: Admin = Depends(current_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    now = datetime.now(timezone.utc)
    base = user.vip_ends_at if user.vip_ends_at and user.vip_ends_at > now else now
    user.vip_ends_at = base + timedelta(days=data.days)
    user.subscription_status = SubscriptionStatus.active
    db.add(AdminAudit(admin_id=admin.id, action="grant_vip", target_type="user", target_id=str(user.id), payload={"days": data.days}))
    await db.commit()
    return {"ok": True, "vip_ends_at": user.vip_ends_at}



@router.get("/admin/users/{user_id}/dialogs")
async def admin_user_dialogs(
    user_id: int,
    _: Admin = Depends(current_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "Пользователь не найден")
    rows = (await db.scalars(
        select(Dialog).where(Dialog.owner_id == user.id).order_by(desc(Dialog.last_event_at), desc(Dialog.id))
    )).all()
    result = []
    for dialog in rows:
        last = await db.scalar(
            select(Message).where(Message.dialog_id == dialog.id).order_by(desc(Message.sent_at), desc(Message.id)).limit(1)
        )
        result.append({
            "id": dialog.id,
            "title": dialog.title,
            "username": dialog.username,
            "muted": dialog.is_muted,
            "hidden": dialog.is_excluded,
            "last_event_at": dialog.last_event_at,
            "last_message": None if last is None else {
                "text": last.current_text,
                "content_type": last.content_type,
                "is_deleted": last.is_deleted,
                "is_outgoing": last.from_user_id == user.telegram_id,
                "sent_at": last.sent_at,
            },
        })
    return {"user": {"id": user.id, "name": user.first_name, "username": user.username}, "dialogs": result}


@router.get("/admin/dialogs/{dialog_id}")
async def admin_dialog_detail(
    dialog_id: int,
    _: Admin = Depends(current_admin),
    db: AsyncSession = Depends(get_db),
):
    dialog = await db.get(Dialog, dialog_id)
    if dialog is None:
        raise HTTPException(404, "Диалог не найден")
    owner = await db.get(User, dialog.owner_id)
    messages = (await db.scalars(
        select(Message).where(Message.dialog_id == dialog.id).order_by(Message.sent_at, Message.id).limit(500)
    )).all()
    ids = [m.id for m in messages]
    media_map = {}
    versions_map = {}
    if ids:
        for row in (await db.scalars(select(MessageMedia).where(MessageMedia.message_id.in_(ids)).order_by(MessageMedia.id))).all():
            media_map.setdefault(row.message_id, []).append(row)
        for row in (await db.scalars(select(MessageVersion).where(MessageVersion.message_id.in_(ids)).order_by(MessageVersion.message_id, MessageVersion.version_no))).all():
            versions_map.setdefault(row.message_id, []).append(row)
    return {
        "dialog": {"id": dialog.id, "title": dialog.title, "username": dialog.username, "owner_id": dialog.owner_id},
        "messages": [{
            "id": m.id, "telegram_message_id": m.telegram_message_id,
            "from_name": m.from_name, "from_username": m.from_username,
            "is_outgoing": bool(owner and m.from_user_id == owner.telegram_id), "text": m.current_text,
            "content_type": m.content_type, "is_deleted": m.is_deleted,
            "sent_at": m.sent_at, "edited_at": m.edited_at, "deleted_at": m.deleted_at,
            "reply_to_message_id": m.reply_to_message_id,
            "media": [{"id": x.id, "type": x.media_type, "file_size": x.file_size, "ephemeral_hint": x.is_ephemeral_hint, "available": bool(x.local_path)} for x in media_map.get(m.id, [])],
            "versions": [{"version_no": x.version_no, "text": x.text, "created_at": x.created_at} for x in versions_map.get(m.id, [])],
        } for m in messages],
    }


@router.get("/admin/media/{media_id}/download")
async def admin_media_download(
    media_id: int,
    _: Admin = Depends(current_admin),
    db: AsyncSession = Depends(get_db),
):
    media = await db.get(MessageMedia, media_id)
    if media is None or not media.local_path:
        raise HTTPException(404, "Медиафайл не найден")
    path = Path(media.local_path)
    if not path.exists() or not path.is_file():
        raise HTTPException(404, "Файл отсутствует в хранилище")
    return FileResponse(
        path,
        filename=path.name,
        media_type=media.mime_type or "application/octet-stream",
        headers={"Cache-Control": "private, no-store"},
    )


@router.get("/subscription")
async def subscription(user: User = Depends(current_user)):
    return {"status": user.subscription_status, "trial_ends_at": user.trial_ends_at, "vip_ends_at": user.vip_ends_at, "provider": "impaya", "payments_enabled": False}

@router.post("/promo/{code}")
async def activate_promo(code: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    promo = await db.scalar(select(PromoCode).where(func.lower(PromoCode.code)==code.lower(), PromoCode.is_active.is_(True)))
    now=datetime.now(timezone.utc)
    if promo is None or (promo.expires_at and promo.expires_at < now) or (promo.max_uses is not None and promo.uses >= promo.max_uses):
        raise HTTPException(404,"Promo code unavailable")
    base=max(filter(None,[user.vip_ends_at,now]))
    user.vip_ends_at=base+timedelta(days=promo.days); user.subscription_status=SubscriptionStatus.active; promo.uses+=1
    await db.commit(); return {"ok":True,"vip_ends_at":user.vip_ends_at}



def _referral_stats(link: ReferralLink, users: list[User], bot_username: str) -> dict:
    total=len(users)
    trial=sum(1 for u in users if u.subscription_status == SubscriptionStatus.trial)
    vip=sum(1 for u in users if u.subscription_status == SubscriptionStatus.active)
    blocked=sum(1 for u in users if u.bot_blocked_at is not None)
    connected=sum(1 for u in users if getattr(u, "_has_business", False))
    spend=link.spend_minor / 100
    return {
        "id":link.id,"code":link.code,"source":link.source,"campaign":link.campaign,
        "placement":link.placement,"spend_minor":link.spend_minor,"currency":link.currency,
        "notes":link.notes,"active":link.is_active,"created_at":link.created_at,
        "url":f"https://t.me/{bot_username}?start=ref_{link.code}",
        "arrived":total,"trial":trial,"vip":vip,"blocked":blocked,"business_connected":connected,
        "conversion_trial":round(trial/total*100,2) if total else 0,
        "conversion_vip":round(vip/total*100,2) if total else 0,
        "block_rate":round(blocked/total*100,2) if total else 0,
        "cost_per_user":round(spend/total,2) if total else 0,
        "cost_per_trial":round(spend/trial,2) if trial else 0,
        "cost_per_vip":round(spend/vip,2) if vip else 0,
    }

@router.post("/admin/referral-links")
async def create_referral_link(data: ReferralLinkCreate, admin: Admin = Depends(current_admin), db: AsyncSession = Depends(get_db)):
    import secrets
    # Resolve Telegram metadata before the transaction is committed. Otherwise a
    # temporary getMe failure returns 500 after the link has already been stored.
    bot_username=(await profile_bot.get_me()).username
    code=secrets.token_urlsafe(9).replace('-','').replace('_','')[:12]
    while await db.scalar(select(ReferralLink).where(ReferralLink.code==code)):
        code=secrets.token_urlsafe(9).replace('-','').replace('_','')[:12]
    row=ReferralLink(code=code,source=data.source.strip(),campaign=(data.campaign or '').strip() or None,placement=(data.placement or '').strip() or None,spend_minor=round(data.spend_rub*100),currency="RUB",notes=(data.notes or '').strip() or None)
    db.add(row); await db.flush()
    db.add(AdminAudit(admin_id=admin.id,action="create_referral_link",target_type="referral_link",target_id=str(row.id),payload={"source":row.source,"spend_minor":row.spend_minor}))
    await db.commit(); await db.refresh(row)
    return {"ok":True,"id":row.id,"code":row.code,"deep_link":f"https://t.me/{bot_username}?start=ref_{row.code}"}

@router.get("/admin/referral-links")
async def referral_links(_: Admin = Depends(current_admin), db: AsyncSession = Depends(get_db)):
    links=(await db.scalars(select(ReferralLink).order_by(desc(ReferralLink.created_at)))).all()
    result=[]
    bot_username=(await profile_bot.get_me()).username
    for link in links:
        users=(await db.scalars(select(User).where(User.referral_link_id==link.id).order_by(User.created_at))).all()
        connection_ids=set((await db.scalars(select(BusinessConnection.owner_id).where(BusinessConnection.owner_id.in_([u.id for u in users] or [-1]),BusinessConnection.is_enabled.is_(True)))).all())
        for u in users: u._has_business=u.id in connection_ids
        stats=_referral_stats(link,list(users),bot_username)
        daily={}
        for u in users:
            key=u.created_at.date().isoformat() if u.created_at else ""
            if key: daily[key]=daily.get(key,0)+1
        stats["daily"]=[{"date":k,"count":v} for k,v in sorted(daily.items())]
        result.append(stats)
    return result

@router.get("/admin/referral-links/{link_id}")
async def referral_link_detail(link_id:int, _: Admin = Depends(current_admin), db: AsyncSession = Depends(get_db)):
    link=await db.get(ReferralLink,link_id)
    if not link: raise HTTPException(404,"Ссылка не найдена")
    users=(await db.scalars(select(User).where(User.referral_link_id==link.id).order_by(desc(User.created_at)))).all()
    connection_ids=set((await db.scalars(select(BusinessConnection.owner_id).where(BusinessConnection.owner_id.in_([u.id for u in users] or [-1]),BusinessConnection.is_enabled.is_(True)))).all())
    for u in users: u._has_business=u.id in connection_ids
    bot_username=(await profile_bot.get_me()).username
    data=_referral_stats(link,list(users),bot_username)
    data["users"]=[{"id":u.id,"telegram_id":u.telegram_id,"name":" ".join(filter(None,[u.first_name,u.last_name])),"username":u.username,"status":u.subscription_status,"blocked":u.bot_blocked_at is not None,"business_connected":u.id in connection_ids,"created_at":u.created_at} for u in users]
    return data

@router.get("/admin/system")
async def admin_system(admin: Admin = Depends(current_admin), db: AsyncSession = Depends(get_db)):
    pending_jobs = 0
    redis_ok = False
    try:
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        pending_jobs = int(await redis.llen("dialogspy:jobs"))
        redis_ok = bool(await redis.ping())
        await redis.aclose()
    except Exception:
        pass

    def meminfo():
        values = {}
        try:
            for line in Path('/proc/meminfo').read_text().splitlines():
                key, value = line.split(':', 1)
                values[key] = int(value.strip().split()[0]) * 1024
        except Exception:
            pass
        total = values.get('MemTotal', 0)
        available = values.get('MemAvailable', 0)
        return total, max(0, total - available)

    memory_total, memory_used = meminfo()
    disk = os.statvfs('/')
    disk_total = disk.f_blocks * disk.f_frsize
    disk_free = disk.f_bavail * disk.f_frsize
    try:
        load1, load5, load15 = os.getloadavg()
    except Exception:
        load1 = load5 = load15 = 0.0

    now = datetime.now(timezone.utc)
    day1 = now - timedelta(hours=24)
    day14 = now - timedelta(days=14)
    hourly = (await db.execute(
        select(func.extract('hour', Event.created_at), func.count(Event.id))
        .where(Event.created_at >= day1)
        .group_by(func.extract('hour', Event.created_at))
        .order_by(func.extract('hour', Event.created_at))
    )).all()
    failures = (await db.execute(
        select(func.date(FailedUpdate.created_at), func.count(FailedUpdate.id))
        .where(FailedUpdate.created_at >= day14)
        .group_by(func.date(FailedUpdate.created_at))
        .order_by(func.date(FailedUpdate.created_at))
    )).all()
    media_types = (await db.execute(
        select(MessageMedia.media_type, func.count(MessageMedia.id))
        .group_by(MessageMedia.media_type)
        .order_by(desc(func.count(MessageMedia.id)))
    )).all()
    return {
      "services": {"api": True, "database": True, "redis": redis_ok, "worker_queue": pending_jobs},
      "server": {
          "load_1": round(load1, 2), "load_5": round(load5, 2), "load_15": round(load15, 2),
          "memory_total": memory_total, "memory_used": memory_used,
          "disk_total": disk_total, "disk_used": max(0, disk_total - disk_free),
      },
      "database": {
          "users": int((await db.scalar(select(func.count(User.id)))) or 0),
          "dialogs": int((await db.scalar(select(func.count(Dialog.id)))) or 0),
          "messages": int((await db.scalar(select(func.count(Message.id)))) or 0),
          "media": int((await db.scalar(select(func.count(MessageMedia.id)))) or 0),
          "events": int((await db.scalar(select(func.count(Event.id)))) or 0),
          "payments": int((await db.scalar(select(func.count(Payment.id)))) or 0),
          "storage_bytes": int((await db.scalar(select(func.coalesce(func.sum(MessageMedia.file_size), 0)))) or 0),
      },
      "failed_updates": int((await db.scalar(select(func.count(FailedUpdate.id)).where(FailedUpdate.resolved.is_(False)))) or 0),
      "pending_jobs": pending_jobs,
      "hourly_24": [{"hour": int(h), "count": int(c)} for h, c in hourly],
      "failures_14": [{"date": str(d), "count": int(c)} for d, c in failures],
      "media_types": [{"type": str(t), "count": int(c)} for t, c in media_types],
    }

@router.get("/admin/metrics")
async def admin_metrics(days:int=Query(default=14,ge=1,le=90), admin: Admin = Depends(current_admin), db: AsyncSession = Depends(get_db)):
    since=datetime.now(timezone.utc)-timedelta(days=days)
    rows=(await db.execute(select(func.date(Event.created_at),Event.event_type,func.count(Event.id)).where(Event.created_at>=since).group_by(func.date(Event.created_at),Event.event_type).order_by(func.date(Event.created_at)))).all()
    return [{"date":str(day),"type":typ.value if hasattr(typ,"value") else str(typ),"count":count} for day,typ,count in rows]

@router.get('/admin/dashboard')
async def admin_dashboard(days:int=Query(default=30,ge=7,le=180), _:Admin=Depends(current_admin), db:AsyncSession=Depends(get_db)):
    now=datetime.now(timezone.utc); since=now-timedelta(days=days); day7=now-timedelta(days=7); day1=now-timedelta(days=1)
    async def count(stmt): return int((await db.scalar(stmt)) or 0)
    overview={
      'users_total':await count(select(func.count(User.id))),
      'users_today':await count(select(func.count(User.id)).where(User.created_at>=day1)),
      'users_week':await count(select(func.count(User.id)).where(User.created_at>=day7)),
      'business_active':await count(select(func.count(BusinessConnection.id)).where(BusinessConnection.is_enabled.is_(True))),
      'trial':await count(select(func.count(User.id)).where(User.subscription_status==SubscriptionStatus.trial)),
      'vip':await count(select(func.count(User.id)).where(User.subscription_status==SubscriptionStatus.active)),
      'messages':await count(select(func.count(Message.id))),
      'deleted':await count(select(func.count(Message.id)).where(Message.is_deleted.is_(True))),
      'edited':await count(select(func.count(Message.id)).where(Message.edited_at.is_not(None))),
      'media':await count(select(func.count(MessageMedia.id))),
      'protected_media':await count(select(func.count(MessageMedia.id)).where(MessageMedia.is_ephemeral_hint.is_(True))),
      'storage_bytes':int((await db.scalar(select(func.coalesce(func.sum(MessageMedia.file_size),0)))) or 0),
      'failed_updates':await count(select(func.count(FailedUpdate.id)).where(FailedUpdate.resolved.is_(False))),
      'payments':await count(select(func.count(Payment.id))),
    }
    daily_users=(await db.execute(select(func.date(User.created_at),func.count(User.id)).where(User.created_at>=since).group_by(func.date(User.created_at)).order_by(func.date(User.created_at)))).all()
    daily_events=(await db.execute(select(func.date(Event.created_at),Event.event_type,func.count(Event.id)).where(Event.created_at>=since).group_by(func.date(Event.created_at),Event.event_type).order_by(func.date(Event.created_at)))).all()
    hourly=(await db.execute(select(func.extract('hour',Event.created_at),func.count(Event.id)).where(Event.created_at>=day7).group_by(func.extract('hour',Event.created_at)).order_by(func.extract('hour',Event.created_at)))).all()
    subscriptions=(await db.execute(select(User.subscription_status,func.count(User.id)).group_by(User.subscription_status))).all()
    media_types=(await db.execute(select(MessageMedia.media_type,func.count(MessageMedia.id)).group_by(MessageMedia.media_type))).all()
    return {'overview':overview,
      'registrations':[{'date':str(d),'count':int(c)} for d,c in daily_users],
      'events':[{'date':str(d),'type':t.value if hasattr(t,'value') else str(t),'count':int(c)} for d,t,c in daily_events],
      'hours':[{'hour':int(h),'count':int(c)} for h,c in hourly],
      'subscriptions':[{'status':s.value if hasattr(s,'value') else str(s),'count':int(c)} for s,c in subscriptions],
      'media_types':[{'type':str(t),'count':int(c)} for t,c in media_types],
    }

@router.get('/admin/dialogs')
async def admin_dialogs(_:Admin=Depends(current_admin),db:AsyncSession=Depends(get_db)):
    rows=(await db.execute(select(Dialog,User).join(User,User.id==Dialog.owner_id).order_by(desc(Dialog.last_event_at)).limit(300))).all()
    return [{'id':d.id,'title':d.title,'username':d.username,'telegram_chat_id':d.telegram_chat_id,'owner_id':u.id,'owner_name':u.first_name,'owner_username':u.username,'muted':d.is_muted,'hidden':d.is_excluded,'last_event_at':d.last_event_at} for d,u in rows]

@router.get('/admin/media')
async def admin_media(_:Admin=Depends(current_admin),db:AsyncSession=Depends(get_db)):
    rows=(await db.execute(select(MessageMedia,Message,Dialog).join(Message,Message.id==MessageMedia.message_id).join(Dialog,Dialog.id==Message.dialog_id).order_by(desc(MessageMedia.created_at)).limit(300))).all()
    return [{'id':m.id,'type':m.media_type,'file_size':m.file_size,'protected':m.is_ephemeral_hint,'available':bool(m.local_path),'dialog':d.title,'created_at':m.created_at} for m,msg,d in rows]

@router.get('/admin/payments')
async def admin_payments(_:Admin=Depends(current_admin),db:AsyncSession=Depends(get_db)):
    rows=(await db.scalars(select(Payment).order_by(desc(Payment.created_at)).limit(300))).all()
    return [{'id':p.id,'owner_id':p.owner_id,'amount_minor':p.amount_minor,'currency':p.currency,'status':p.status,'recurring':p.is_recurring,'created_at':p.created_at} for p in rows]

@router.get('/admin/errors')
async def admin_errors(_:Admin=Depends(current_admin),db:AsyncSession=Depends(get_db)):
    rows=(await db.scalars(select(FailedUpdate).order_by(desc(FailedUpdate.created_at)).limit(300))).all()
    return [{'id':r.id,'update_id':r.update_id,'type':r.update_type,'error':r.error,'resolved':r.resolved,'created_at':r.created_at} for r in rows]
