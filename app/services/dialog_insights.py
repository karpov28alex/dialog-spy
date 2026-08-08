from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import case, func, select

from app.db.models import Dialog, Message as DbMessage, User
from app.db.session import SessionLocal


async def dialog_insights(telegram_id: int, days: int = 30) -> dict[str, object] | None:
    """Compact behavioural insights used by bot surfaces without loading message bodies."""
    now = datetime.now(UTC)
    since = now - timedelta(days=days)
    recent = now - timedelta(days=7)
    previous = now - timedelta(days=14)
    stale = now - timedelta(days=14)
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if not user:
            return None
        total = int(await session.scalar(select(func.count(DbMessage.id)).join(Dialog, Dialog.id == DbMessage.dialog_id).where(Dialog.owner_user_id == user.id, DbMessage.sent_at >= since)) or 0)
        recent_count = int(await session.scalar(select(func.count(DbMessage.id)).join(Dialog, Dialog.id == DbMessage.dialog_id).where(Dialog.owner_user_id == user.id, DbMessage.sent_at >= recent)) or 0)
        previous_count = int(await session.scalar(select(func.count(DbMessage.id)).join(Dialog, Dialog.id == DbMessage.dialog_id).where(Dialog.owner_user_id == user.id, DbMessage.sent_at >= previous, DbMessage.sent_at < recent)) or 0)
        active = int(await session.scalar(select(func.count(Dialog.id)).where(Dialog.owner_user_id == user.id, Dialog.last_message_at >= recent)) or 0)
        quiet = int(await session.scalar(select(func.count(Dialog.id)).where(Dialog.owner_user_id == user.id, Dialog.last_message_at.is_not(None), Dialog.last_message_at < stale)) or 0)
        top = (await session.execute(select(Dialog.id.label("dialog_id"), Dialog.peer_name, Dialog.peer_username, func.count(DbMessage.id).label("n")).join(DbMessage, DbMessage.dialog_id == Dialog.id).where(Dialog.owner_user_id == user.id, DbMessage.sent_at >= since).group_by(Dialog.id, Dialog.peer_name, Dialog.peer_username).order_by(func.count(DbMessage.id).desc()).limit(1))).first()
        hour = await session.scalar(select(func.extract("hour", DbMessage.sent_at).label("hour")).join(Dialog, Dialog.id == DbMessage.dialog_id).where(Dialog.owner_user_id == user.id, DbMessage.sent_at >= since).group_by("hour").order_by(func.count(DbMessage.id).desc()).limit(1))
        recent_deleted = int(await session.scalar(select(func.count(DbMessage.id)).join(Dialog, Dialog.id == DbMessage.dialog_id).where(Dialog.owner_user_id == user.id, DbMessage.sent_at >= recent, DbMessage.is_deleted.is_(True))) or 0)
        recent_edited = int(await session.scalar(select(func.count(DbMessage.id)).join(Dialog, Dialog.id == DbMessage.dialog_id).where(Dialog.owner_user_id == user.id, DbMessage.sent_at >= recent, DbMessage.edited_at.is_not(None))) or 0)
        direction = (await session.execute(select(DbMessage.direction, func.count(DbMessage.id)).join(Dialog, Dialog.id == DbMessage.dialog_id).where(Dialog.owner_user_id == user.id, DbMessage.sent_at >= recent).group_by(DbMessage.direction))).all()
        comparison = (await session.execute(select(Dialog.id.label("dialog_id"), Dialog.peer_name, Dialog.peer_username, func.sum(case((DbMessage.sent_at >= recent, 1), else_=0)).label("recent"), func.count(DbMessage.id).label("all14")).join(DbMessage, DbMessage.dialog_id == Dialog.id).where(Dialog.owner_user_id == user.id, DbMessage.sent_at >= previous).group_by(Dialog.id, Dialog.peer_name, Dialog.peer_username))).all()

    rising = None
    fading = None
    for row in comparison:
        current = int(row.recent or 0)
        old = max(int(row.all14 or 0) - current, 0)
        delta = current - old
        item = {"dialog_id": int(row.dialog_id), "name": row.peer_name or (f"@{row.peer_username}" if row.peer_username else "Диалог"), "recent": current, "previous": old, "delta": delta}
        if current >= 4 and delta >= 3 and (rising is None or delta > int(rising["delta"])):
            rising = item
        if old >= 5 and current <= max(1, old // 3) and (fading is None or old - current > int(fading["previous"]) - int(fading["recent"])):
            fading = item

    direction_map = {str(name): int(value or 0) for name, value in direction}
    incoming = direction_map.get("incoming", 0)
    outgoing = direction_map.get("outgoing", 0)
    weekly_change = 0 if previous_count == 0 else round((recent_count - previous_count) / previous_count * 100)
    return {
        "days": days,
        "messages": total,
        "recent_messages": recent_count,
        "previous_messages": previous_count,
        "weekly_change": weekly_change,
        "active_dialogs": active,
        "quiet_dialogs": quiet,
        "top_name": (top.peer_name or (f"@{top.peer_username}" if top and top.peer_username else "—")) if top else "—",
        "top_messages": int(top.n or 0) if top else 0,
        "top_dialog_id": int(top.dialog_id) if top else None,
        "peak_hour": int(hour) if hour is not None else None,
        "recent_deleted": recent_deleted,
        "recent_edited": recent_edited,
        "incoming": incoming,
        "outgoing": outgoing,
        "rising": rising,
        "fading": fading,
    }


def format_dialog_insights(data: dict[str, object]) -> str:
    peak = f"{int(data['peak_hour']):02d}:00" if data.get("peak_hour") is not None else "—"
    change = int(data.get("weekly_change") or 0)
    pace = f"{change:+d}% к прошлой неделе" if change else "без резкого изменения темпа"
    lines = [
        f"<b>🧠 Phantom Insights · {data['days']} дней</b>",
        "",
        f"⚡ Последние 7 дней: <b>{data['recent_messages']}</b> сообщений · {pace}",
        f"💜 Главный диалог: <b>{data['top_name']}</b> · {data['top_messages']} сообщений",
        f"🕒 Пик общения: <b>{peak}</b>",
        f"🌙 Затихших диалогов: <b>{data['quiet_dialogs']}</b>",
    ]
    rising = data.get("rising")
    fading = data.get("fading")
    if isinstance(rising, dict):
        lines.append(f"🚀 <b>{rising['name']}</b>: активность выросла {rising['previous']} → {rising['recent']}")
    if isinstance(fading, dict):
        lines.append(f"🌘 <b>{fading['name']}</b>: активность снизилась {fading['previous']} → {fading['recent']}")
    if int(data.get("recent_deleted") or 0):
        lines.append(f"🗑 Удалено за 7 дней: <b>{data['recent_deleted']}</b>")
    if int(data.get("recent_edited") or 0):
        lines.append(f"✏️ Изменено за 7 дней: <b>{data['recent_edited']}</b>")
    incoming = int(data.get("incoming") or 0)
    outgoing = int(data.get("outgoing") or 0)
    if incoming + outgoing >= 10:
        initiator = "вам пишут чаще" if incoming > outgoing else "вы пишете чаще"
        lines.append(f"↔️ За неделю {initiator}: {incoming} входящих / {outgoing} исходящих")
    return "\n".join(lines[:11])
