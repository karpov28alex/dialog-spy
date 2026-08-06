from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Dialog, Media, Message, MessageVersion


class ArchiveRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_dialogs(self, *, owner_user_id: int, limit: int, cursor: int | None) -> list[Dialog]:
        statement = (
            select(Dialog)
            .where(Dialog.owner_user_id == owner_user_id)
            .order_by(desc(Dialog.last_message_at), desc(Dialog.id))
            .limit(limit + 1)
        )
        if cursor is not None:
            statement = statement.where(Dialog.id < cursor)
        return list((await self._session.scalars(statement)).all())

    async def get_dialog(self, *, dialog_id: int, owner_user_id: int) -> Dialog | None:
        return await self._session.scalar(
            select(Dialog).where(Dialog.id == dialog_id, Dialog.owner_user_id == owner_user_id)
        )

    async def list_messages(self, *, dialog_id: int, limit: int, before_id: int | None) -> list[Message]:
        statement = (
            select(Message)
            .where(Message.dialog_id == dialog_id)
            .order_by(desc(Message.id))
            .limit(limit + 1)
        )
        if before_id is not None:
            statement = statement.where(Message.id < before_id)
        return list((await self._session.scalars(statement)).all())

    async def media_for_messages(self, message_ids: list[int]) -> list[Media]:
        if not message_ids:
            return []
        return list(
            (await self._session.scalars(select(Media).where(Media.message_id.in_(message_ids)))).all()
        )

    async def versions_for_messages(self, message_ids: list[int]) -> list[MessageVersion]:
        if not message_ids:
            return []
        statement = (
            select(MessageVersion)
            .where(MessageVersion.message_id.in_(message_ids))
            .order_by(MessageVersion.message_id, MessageVersion.version_number)
        )
        return list((await self._session.scalars(statement)).all())

    async def get_message(self, *, message_id: int, owner_user_id: int) -> Message | None:
        return await self._session.scalar(
            select(Message)
            .join(Dialog, Dialog.id == Message.dialog_id)
            .where(Message.id == message_id, Dialog.owner_user_id == owner_user_id)
        )

    async def versions_for_message(self, message_id: int) -> list[MessageVersion]:
        return list(
            (
                await self._session.scalars(
                    select(MessageVersion)
                    .where(MessageVersion.message_id == message_id)
                    .order_by(MessageVersion.version_number)
                )
            ).all()
        )

    async def last_messages(self, dialog_ids: list[int]) -> dict[int, Message]:
        if not dialog_ids:
            return {}
        statement = (
            select(Message)
            .where(Message.dialog_id.in_(dialog_ids))
            .distinct(Message.dialog_id)
            .order_by(Message.dialog_id, desc(Message.sent_at), desc(Message.id))
        )
        rows = list((await self._session.scalars(statement)).all())
        return {row.dialog_id: row for row in rows}

    async def dialog_metrics(self, dialog_ids: list[int]) -> dict[int, dict[str, int]]:
        if not dialog_ids:
            return {}
        metrics: dict[int, dict[str, int]] = {
            dialog_id: {
                "message_count": 0,
                "edited_count": 0,
                "deleted_count": 0,
                "media_count": 0,
                "protected_media_count": 0,
            }
            for dialog_id in dialog_ids
        }
        message_rows = (
            await self._session.execute(
                select(
                    Message.dialog_id,
                    func.count(Message.id),
                    func.count(Message.id).filter(Message.edited_at.is_not(None)),
                    func.count(Message.id).filter(Message.is_deleted.is_(True)),
                )
                .where(Message.dialog_id.in_(dialog_ids))
                .group_by(Message.dialog_id)
            )
        ).all()
        for dialog_id, total, edited, deleted in message_rows:
            metrics[int(dialog_id)].update(
                message_count=int(total or 0),
                edited_count=int(edited or 0),
                deleted_count=int(deleted or 0),
            )
        media_rows = (
            await self._session.execute(
                select(
                    Message.dialog_id,
                    func.count(Media.id),
                    func.count(Media.id).filter(Media.is_protected.is_(True)),
                )
                .join(Message, Message.id == Media.message_id)
                .where(Message.dialog_id.in_(dialog_ids))
                .group_by(Message.dialog_id)
            )
        ).all()
        for dialog_id, total, protected in media_rows:
            metrics[int(dialog_id)].update(
                media_count=int(total or 0),
                protected_media_count=int(protected or 0),
            )
        return metrics

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

    async def commit(self) -> None:
        await self._session.commit()
