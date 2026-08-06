from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import event, inspect, select
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.activity_models import UserActivityLog
from app.db.models import BusinessConnection, Dialog, User


def _now() -> datetime:
    return datetime.now(UTC)


def _insert(
    connection: Connection,
    *,
    user_id: int,
    telegram_id: int,
    event_type: str,
    category: str,
    title: str,
    description: str | None = None,
    object_type: str | None = None,
    object_id: str | None = None,
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    connection.execute(
        UserActivityLog.__table__.insert().values(
            user_id=user_id,
            telegram_id=telegram_id,
            event_type=event_type,
            category=category,
            title=title,
            description=description,
            object_type=object_type,
            object_id=object_id,
            old_value=old_value,
            new_value=new_value,
            metadata_json=metadata or {},
            created_at=_now(),
        )
    )


def _owner_telegram_id(connection: Connection, user_id: int) -> int | None:
    return connection.execute(
        select(User.telegram_id).where(User.id == user_id)
    ).scalar_one_or_none()


@event.listens_for(BusinessConnection, "after_insert")
def business_connection_insert(mapper, connection: Connection, target: BusinessConnection) -> None:
    telegram_id = _owner_telegram_id(connection, target.owner_user_id)
    if telegram_id is None:
        return
    _insert(
        connection,
        user_id=target.owner_user_id,
        telegram_id=telegram_id,
        event_type="connection_enabled" if target.is_active else "connection_disabled",
        category="connection",
        title="Автоматизация чатов подключена" if target.is_active else "Автоматизация чатов отключена",
        object_type="business_connection",
        object_id=target.telegram_connection_id,
        new_value={"active": target.is_active, "rights": target.rights or {}},
    )


@event.listens_for(BusinessConnection, "after_update")
def business_connection_update(mapper, connection: Connection, target: BusinessConnection) -> None:
    state = inspect(target)
    telegram_id = _owner_telegram_id(connection, target.owner_user_id)
    if telegram_id is None:
        return
    active_history = state.attrs.is_active.history
    rights_history = state.attrs.rights.history
    if active_history.has_changes():
        old = bool(active_history.deleted[0]) if active_history.deleted else not target.is_active
        _insert(
            connection,
            user_id=target.owner_user_id,
            telegram_id=telegram_id,
            event_type="connection_enabled" if target.is_active else "connection_disabled",
            category="connection",
            title="Автоматизация чатов подключена" if target.is_active else "Автоматизация чатов отключена",
            object_type="business_connection",
            object_id=target.telegram_connection_id,
            old_value={"active": old},
            new_value={"active": target.is_active},
        )
    if rights_history.has_changes():
        old_rights = rights_history.deleted[0] if rights_history.deleted else {}
        new_rights = target.rights or {}
        _insert(
            connection,
            user_id=target.owner_user_id,
            telegram_id=telegram_id,
            event_type="connection_rights_changed",
            category="permissions",
            title="Изменены права автоматизации",
            object_type="business_connection",
            object_id=target.telegram_connection_id,
            old_value=old_rights,
            new_value=new_rights,
        )


@event.listens_for(Dialog, "after_insert")
def dialog_insert(mapper, connection: Connection, target: Dialog) -> None:
    telegram_id = _owner_telegram_id(connection, target.owner_user_id)
    if telegram_id is None:
        return
    _insert(
        connection,
        user_id=target.owner_user_id,
        telegram_id=telegram_id,
        event_type="dialog_discovered",
        category="dialogs",
        title="Новый диалог появился в архиве",
        description=target.peer_name or target.peer_username or str(target.telegram_chat_id),
        object_type="dialog",
        object_id=str(target.id),
        new_value={
            "chat_id": target.telegram_chat_id,
            "peer_name": target.peer_name,
            "peer_username": target.peer_username,
        },
    )


@event.listens_for(Dialog, "after_update")
def dialog_update(mapper, connection: Connection, target: Dialog) -> None:
    state = inspect(target)
    telegram_id = _owner_telegram_id(connection, target.owner_user_id)
    if telegram_id is None:
        return
    for field, enabled_title, disabled_title, event_on, event_off in (
        ("is_hidden", "Диалог скрыт", "Диалог возвращён", "dialog_hidden", "dialog_restored"),
        ("is_muted", "Уведомления диалога выключены", "Уведомления диалога включены", "dialog_muted", "dialog_unmuted"),
    ):
        history = state.attrs[field].history
        if not history.has_changes():
            continue
        value = bool(getattr(target, field))
        _insert(
            connection,
            user_id=target.owner_user_id,
            telegram_id=telegram_id,
            event_type=event_on if value else event_off,
            category="dialogs",
            title=enabled_title if value else disabled_title,
            description=target.peer_name or target.peer_username or str(target.telegram_chat_id),
            object_type="dialog",
            object_id=str(target.id),
            old_value={field: not value},
            new_value={field: value},
            metadata={"chat_id": target.telegram_chat_id},
        )


async def add_activity(
    session: AsyncSession,
    *,
    user: User,
    event_type: str,
    category: str,
    title: str,
    description: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> UserActivityLog:
    row = UserActivityLog(
        user_id=user.id,
        telegram_id=user.telegram_id,
        event_type=event_type,
        category=category,
        title=title,
        description=description,
        metadata_json=metadata or {},
        created_at=_now(),
    )
    session.add(row)
    await session.flush()
    return row
