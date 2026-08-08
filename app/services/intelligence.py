from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import case, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Dialog, Media, Message, User
from app.services.access import access_state


def _contact(row: Any) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "dialog_id": int(row.dialog_id),
        "name": row.peer_name or row.peer_username or "Без имени",
        "username": row.peer_username,
        "value": int(row.value or 0),
    }


def _name(row: Any) -> str:
    if row is None:
        return "диалог"
    return row.peer_name or row.peer_username or "диалог"


async def build_user_intelligence(
    session: AsyncSession,
    user: User,
    *,
    days: int = 30,
) -> dict[str, Any]:
    days = max(7, min(int(days), 3650))
    now = datetime.now(UTC)
    since = now - timedelta(days=days)
    recent_since = now - timedelta(days=7)
    previous_since = now - timedelta(days=14)

    dialogs_total = int(
        await session.scalar(select(func.count(Dialog.id)).where(Dialog.owner_user_id == user.id)) or 0
    )
    message_scope = select(Message.id).join(Dialog, Dialog.id == Message.dialog_id).where(Dialog.owner_user_id == user.id)
    messages_total = int(await session.scalar(select(func.count()).select_from(message_scope.subquery())) or 0)
    deleted_total = int(
        await session.scalar(
            select(func.count(Message.id))
            .join(Dialog, Dialog.id == Message.dialog_id)
            .where(Dialog.owner_user_id == user.id, Message.is_deleted.is_(True))
        ) or 0
    )
    edited_total = int(
        await session.scalar(
            select(func.count(Message.id))
            .join(Dialog, Dialog.id == Message.dialog_id)
            .where(Dialog.owner_user_id == user.id, Message.edited_at.is_not(None))
        ) or 0
    )
    media_total = int(
        await session.scalar(
            select(func.count(Media.id))
            .join(Message, Message.id == Media.message_id)
            .join(Dialog, Dialog.id == Message.dialog_id)
            .where(Dialog.owner_user_id == user.id)
        ) or 0
    )
    protected_total = int(
        await session.scalar(
            select(func.count(Media.id))
            .join(Message, Message.id == Media.message_id)
            .join(Dialog, Dialog.id == Message.dialog_id)
            .where(Dialog.owner_user_id == user.id, Media.is_protected.is_(True))
        ) or 0
    )

    period_rows = (
        await session.execute(
            select(
                func.date(Message.sent_at).label("day"),
                func.count(Message.id).label("messages"),
                func.sum(case((Message.is_deleted.is_(True), 1), else_=0)).label("deleted"),
                func.sum(case((Message.edited_at.is_not(None), 1), else_=0)).label("edited"),
            )
            .join(Dialog, Dialog.id == Message.dialog_id)
            .where(Dialog.owner_user_id == user.id, Message.sent_at >= since)
            .group_by(func.date(Message.sent_at))
            .order_by(func.date(Message.sent_at))
        )
    ).all()

    hourly_rows = (
        await session.execute(
            select(
                extract("hour", Message.sent_at).label("hour"),
                func.count(Message.id).label("messages"),
            )
            .join(Dialog, Dialog.id == Message.dialog_id)
            .where(Dialog.owner_user_id == user.id, Message.sent_at >= since)
            .group_by(extract("hour", Message.sent_at))
            .order_by(extract("hour", Message.sent_at))
        )
    ).all()

    async def message_leader(*extra_where):
        return (
            await session.execute(
                select(
                    Dialog.id.label("dialog_id"),
                    Dialog.peer_name,
                    Dialog.peer_username,
                    func.count(Message.id).label("value"),
                )
                .join(Message, Message.dialog_id == Dialog.id)
                .where(Dialog.owner_user_id == user.id, *extra_where)
                .group_by(Dialog.id, Dialog.peer_name, Dialog.peer_username)
                .order_by(func.count(Message.id).desc(), Dialog.id)
                .limit(1)
            )
        ).first()

    async def media_leader(*extra_where):
        return (
            await session.execute(
                select(
                    Dialog.id.label("dialog_id"),
                    Dialog.peer_name,
                    Dialog.peer_username,
                    func.count(Media.id).label("value"),
                )
                .join(Message, Message.dialog_id == Dialog.id)
                .join(Media, Media.message_id == Message.id)
                .where(Dialog.owner_user_id == user.id, *extra_where)
                .group_by(Dialog.id, Dialog.peer_name, Dialog.peer_username)
                .order_by(func.count(Media.id).desc(), Dialog.id)
                .limit(1)
            )
        ).first()

    active = await message_leader()
    media_top = await media_leader()
    deleted_leader = await message_leader(Message.is_deleted.is_(True))
    protected_leader = await media_leader(Media.is_protected.is_(True))

    longest = (
        await session.execute(
            select(
                Dialog.id.label("dialog_id"),
                Dialog.peer_name,
                Dialog.peer_username,
                func.count(Message.id).label("value"),
                func.min(Message.sent_at).label("started_at"),
                func.max(Message.sent_at).label("last_at"),
            )
            .join(Message, Message.dialog_id == Dialog.id)
            .where(Dialog.owner_user_id == user.id)
            .group_by(Dialog.id, Dialog.peer_name, Dialog.peer_username)
            .order_by(func.count(Message.id).desc(), Dialog.id)
            .limit(1)
        )
    ).first()

    comparison_rows = (
        await session.execute(
            select(
                Dialog.id.label("dialog_id"),
                Dialog.peer_name,
                Dialog.peer_username,
                func.sum(case((Message.sent_at >= recent_since, 1), else_=0)).label("recent"),
                func.sum(case((Message.sent_at >= previous_since, 1), else_=0)).label("previous_window"),
            )
            .join(Message, Message.dialog_id == Dialog.id)
            .where(Dialog.owner_user_id == user.id, Message.sent_at >= previous_since)
            .group_by(Dialog.id, Dialog.peer_name, Dialog.peer_username)
        )
    ).all()

    recent_messages = int(
        await session.scalar(
            select(func.count(Message.id))
            .join(Dialog, Dialog.id == Message.dialog_id)
            .where(Dialog.owner_user_id == user.id, Message.sent_at >= recent_since)
        ) or 0
    )
    previous_messages = int(
        await session.scalar(
            select(func.count(Message.id))
            .join(Dialog, Dialog.id == Message.dialog_id)
            .where(Dialog.owner_user_id == user.id, Message.sent_at >= previous_since, Message.sent_at < recent_since)
        ) or 0
    )
    inbound = int(
        await session.scalar(
            select(func.count(Message.id))
            .join(Dialog, Dialog.id == Message.dialog_id)
            .where(Dialog.owner_user_id == user.id, Message.sent_at >= recent_since, Message.direction == "incoming")
        ) or 0
    )
    outbound = int(
        await session.scalar(
            select(func.count(Message.id))
            .join(Dialog, Dialog.id == Message.dialog_id)
            .where(Dialog.owner_user_id == user.id, Message.sent_at >= recent_since, Message.direction == "outgoing")
        ) or 0
    )
    recent_deleted = int(
        await session.scalar(
            select(func.count(Message.id))
            .join(Dialog, Dialog.id == Message.dialog_id)
            .where(Dialog.owner_user_id == user.id, Message.sent_at >= recent_since, Message.is_deleted.is_(True))
        ) or 0
    )
    recent_edited = int(
        await session.scalar(
            select(func.count(Message.id))
            .join(Dialog, Dialog.id == Message.dialog_id)
            .where(Dialog.owner_user_id == user.id, Message.sent_at >= recent_since, Message.edited_at.is_not(None))
        ) or 0
    )

    access = await access_state(session, user)
    locked = not access.active
    totals = {"dialogs": dialogs_total, "messages": messages_total, "media": media_total, "deleted": deleted_total, "edited": edited_total, "protected": protected_total}
    peak_hour = max(hourly_rows, key=lambda row: int(row.messages or 0), default=None)

    rising = None
    fading = None
    for row in comparison_rows:
        current = int(row.recent or 0)
        previous = max(int(row.previous_window or 0) - current, 0)
        delta = current - previous
        ratio = (current + 1) / (previous + 1)
        item = {"dialog_id": int(row.dialog_id), "name": _name(row), "username": row.peer_username, "recent": current, "previous": previous, "delta": delta, "ratio": round(ratio, 2)}
        if current >= 4 and delta >= 3 and (rising is None or delta > rising["delta"]):
            rising = item
        if previous >= 5 and current <= max(1, previous // 3) and (fading is None or previous - current > fading["previous"] - fading["recent"]):
            fading = item

    weekly_delta = recent_messages - previous_messages
    weekly_change = 0 if previous_messages == 0 else round(weekly_delta / previous_messages * 100)
    direction_total = inbound + outbound
    incoming_share = round(inbound / direction_total * 100) if direction_total else 0

    signals: list[dict[str, Any]] = []
    if rising:
        signals.append({"kind": "rising", "icon": "🚀", "title": "Общение ускорилось", "text": f"С {_name(type('R', (), rising)())} за 7 дней стало заметно больше сообщений: {rising['previous']} → {rising['recent']}.", "dialog_id": rising["dialog_id"]})
    if fading:
        signals.append({"kind": "fading", "icon": "🌙", "title": "Диалог затих", "text": f"С {_name(type('R', (), fading)())} активность снизилась: {fading['previous']} → {fading['recent']} сообщений.", "dialog_id": fading["dialog_id"]})
    if previous_messages and abs(weekly_change) >= 35:
        direction = "выше" if weekly_change > 0 else "ниже"
        signals.append({"kind": "pace", "icon": "⚡", "title": "Темп изменился", "text": f"Активность за последние 7 дней на {abs(weekly_change)}% {direction} предыдущей недели."})
    if direction_total >= 10:
        if incoming_share >= 65:
            signals.append({"kind": "direction", "icon": "📥", "title": "Вам пишут чаще", "text": f"{incoming_share}% сообщений за неделю пришли от собеседников."})
        elif incoming_share <= 35:
            signals.append({"kind": "direction", "icon": "📤", "title": "Вы инициируете чаще", "text": f"{100 - incoming_share}% сообщений за неделю отправлены с вашей стороны."})
    if recent_deleted >= 3:
        signals.append({"kind": "deleted", "icon": "🗑", "title": "Удалений стало заметно", "text": f"За 7 дней Phantom сохранил {recent_deleted} удалённых сообщений."})
    if recent_edited >= 5:
        signals.append({"kind": "edited", "icon": "✏️", "title": "Много изменений", "text": f"За 7 дней изменено {recent_edited} сообщений — Phantom сохранил историю правок."})
    if peak_hour is not None:
        signals.append({"kind": "peak", "icon": "🕒", "title": "Ваш пик общения", "text": f"Чаще всего активность приходится примерно на {int(peak_hour.hour):02d}:00."})

    insights: list[str] = []
    if signals:
        insights.extend(str(item["text"]) for item in signals[:5])
    else:
        if active:
            insights.append(f"Чаще всего вы общаетесь с {_name(active)}.")
        if media_top:
            insights.append(f"Больше всего медиа связано с {_name(media_top)}.")
        if deleted_leader:
            insights.append(f"Чаще остальных сообщения удаляет {_name(deleted_leader)}.")
        if peak_hour is not None:
            insights.append(f"Пик активности приходится примерно на {int(peak_hour.hour):02d}:00.")
        if totals["edited"]:
            insights.append(f"В архиве сохранено {totals['edited']} изменений сообщений.")
    if not insights:
        insights.append("Пока недостаточно данных для персональных выводов.")

    def maybe_contact(row):
        contact = _contact(row)
        if contact and locked:
            contact["name"] = "********"
            contact["username"] = None
        return contact

    longest_payload = None
    if longest:
        started = longest.started_at
        last = longest.last_at
        longest_payload = maybe_contact(longest)
        longest_payload.update({"started_at": started, "last_at": last, "days": max((last - started).days, 0) if started and last else 0})

    safe_signals = signals[:6]
    if locked:
        safe_signals = [{"kind": "locked", "icon": "🔒", "title": "Phantom Insights", "text": "Подробные персональные сигналы доступны после оплаты."}]

    return {
        "generated_at": now,
        "period_days": days,
        "locked": locked,
        "access": {"active": access.active, "source": access.source, "ends_at": access.ends_at},
        "totals": totals,
        "comparison": {"recent_messages": recent_messages, "previous_messages": previous_messages, "delta": weekly_delta, "change_percent": weekly_change, "incoming": inbound, "outgoing": outbound, "incoming_share": incoming_share},
        "activity": [{"date": str(row.day), "messages": int(row.messages or 0), "deleted": int(row.deleted or 0), "edited": int(row.edited or 0)} for row in period_rows],
        "hours": [{"hour": int(row.hour), "messages": int(row.messages or 0)} for row in hourly_rows],
        "leaders": {"active": maybe_contact(active), "media": maybe_contact(media_top), "deleted": maybe_contact(deleted_leader), "protected": maybe_contact(protected_leader), "longest": longest_payload},
        "signals": safe_signals,
        "insights": insights[:5] if not locked else ["Подробные персональные выводы доступны после оплаты."],
    }
