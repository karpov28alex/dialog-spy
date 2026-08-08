from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.db.models import Dialog, Message as DbMessage, User
from app.db.session import SessionLocal


async def dialog_insights(telegram_id: int, days: int = 30) -> dict[str, object] | None:
    """Compact behavioural insights used by bot surfaces without loading message bodies."""
    now = datetime.now(UTC)
    since = now - timedelta(days=days)
    recent = now - timedelta(days=min(days, 7))
    stale = now - timedelta(days=14)
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if not user:
            return None
        total = int(await session.scalar(select(func.count(DbMessage.id)).join(Dialog, Dialog.id == DbMessage.dialog_id).where(Dialog.owner_user_id == user.id, DbMessage.sent_at >= since)) or 0)
        recent_count = int(await session.scalar(select(func.count(DbMessage.id)).join(Dialog, Dialog.id == DbMessage.dialog_id).where(Dialog.owner_user_id == user.id, DbMessage.sent_at >= recent)) or 0)
        active = int(await session.scalar(select(func.count(Dialog.id)).where(Dialog.owner_user_id == user.id, Dialog.last_message_at >= recent)) or 0)
        quiet = int(await session.scalar(select(func.count(Dialog.id)).where(Dialog.owner_user_id == user.id, Dialog.last_message_at.is_not(None), Dialog.last_message_at < stale)) or 0)
        top = (await session.execute(select(Dialog.peer_name, Dialog.peer_username, func.count(DbMessage.id).label("n")).join(DbMessage, DbMessage.dialog_id == Dialog.id).where(Dialog.owner_user_id == user.id, DbMessage.sent_at >= since).group_by(Dialog.id, Dialog.peer_name, Dialog.peer_username).order_by(func.count(DbMessage.id).desc()).limit(1))).first()
        hour = await session.scalar(select(func.extract("hour", DbMessage.sent_at).label("hour")).join(Dialog, Dialog.id == DbMessage.dialog_id).where(Dialog.owner_user_id == user.id, DbMessage.sent_at >= since).group_by("hour").order_by(func.count(DbMessage.id).desc()).limit(1))
    return {
        "days": days,
        "messages": total,
        "recent_messages": recent_count,
        "active_dialogs": active,
        "quiet_dialogs": quiet,
        "top_name": (top.peer_name or (f"@{top.peer_username}" if top and top.peer_username else "—")) if top else "—",
        "top_messages": int(top.n or 0) if top else 0,
        "peak_hour": int(hour) if hour is not None else None,
    }


def format_dialog_insights(data: dict[str, object]) -> str:
    peak = f"{int(data['peak_hour']):02d}:00" if data.get("peak_hour") is not None else "—"
    return (
        f"<b>🧠 Phantom Insights · {data['days']} дней</b>\n\n"
        f"💬 Сообщений: <b>{data['messages']}</b>\n"
        f"⚡ Активных диалогов за 7 дней: <b>{data['active_dialogs']}</b>\n"
        f"💜 Главный диалог: <b>{data['top_name']}</b> · {data['top_messages']} сообщений\n"
        f"🕒 Пик общения: <b>{peak}</b>\n"
        f"🌙 Затихших диалогов: <b>{data['quiet_dialogs']}</b>"
    )
