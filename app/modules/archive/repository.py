from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Dialog, Message


class ArchiveRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_dialogs(
        self,
        *,
        owner_user_id: int,
        limit: int,
        cursor: int | None,
    ) -> list[Dialog]:
        statement = (
            select(Dialog)
            .where(Dialog.owner_user_id == owner_user_id)
            .order_by(desc(Dialog.last_message_at), desc(Dialog.id))
            .limit(limit + 1)
        )
        if cursor is not None:
            statement = statement.where(Dialog.id < cursor)
        return list((await self._session.scalars(statement)).all())

    async def last_message(self, dialog_id: int) -> Message | None:
        return await self._session.scalar(
            select(Message)
            .where(Message.dialog_id == dialog_id)
            .order_by(desc(Message.sent_at), desc(Message.id))
            .limit(1)
        )

    async def message_count(self, dialog_id: int) -> int:
        value = await self._session.scalar(
            select(func.count(Message.id)).where(Message.dialog_id == dialog_id)
        )
        return int(value or 0)
