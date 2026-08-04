from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Dialog, Media, Message, MessageVersion


class SearchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def dialogs(self, owner_user_id: int, pattern: str, limit: int):
        return list((await self._session.scalars(
            select(Dialog)
            .where(
                Dialog.owner_user_id == owner_user_id,
                or_(Dialog.peer_name.ilike(pattern), Dialog.peer_username.ilike(pattern)),
            )
            .order_by(desc(Dialog.last_message_at), desc(Dialog.id))
            .limit(limit)
        )).all())

    async def messages(self, owner_user_id: int, pattern: str, limit: int):
        return list((await self._session.execute(
            select(Message, Dialog)
            .join(Dialog, Dialog.id == Message.dialog_id)
            .where(
                Dialog.owner_user_id == owner_user_id,
                or_(Message.text.ilike(pattern), Message.caption.ilike(pattern)),
            )
            .order_by(desc(Message.sent_at), desc(Message.id))
            .limit(limit)
        )).all())

    async def versions(self, owner_user_id: int, pattern: str, limit: int):
        return list((await self._session.execute(
            select(MessageVersion, Message, Dialog)
            .join(Message, Message.id == MessageVersion.message_id)
            .join(Dialog, Dialog.id == Message.dialog_id)
            .where(
                Dialog.owner_user_id == owner_user_id,
                or_(MessageVersion.text.ilike(pattern), MessageVersion.caption.ilike(pattern)),
            )
            .order_by(desc(MessageVersion.created_at), desc(MessageVersion.id))
            .limit(limit)
        )).all())

    async def media(self, owner_user_id: int, pattern: str, limit: int):
        return list((await self._session.execute(
            select(Media, Message, Dialog)
            .join(Message, Message.id == Media.message_id)
            .join(Dialog, Dialog.id == Message.dialog_id)
            .where(
                Dialog.owner_user_id == owner_user_id,
                or_(
                    Media.filename.ilike(pattern),
                    Media.mime_type.ilike(pattern),
                    Media.media_type.ilike(pattern),
                ),
            )
            .order_by(desc(Media.created_at), desc(Media.id))
            .limit(limit)
        )).all())
