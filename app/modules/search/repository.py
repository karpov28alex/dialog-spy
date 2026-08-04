from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Dialog, Media, Message, MessageVersion
from app.modules.search.schemas import SearchFilters


class SearchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _document(*columns):
        document = func.coalesce(columns[0], "")
        for column in columns[1:]:
            document = document + " " + func.coalesce(column, "")
        return document

    @classmethod
    def _matches(cls, *columns, query: str):
        vector = func.to_tsvector("simple", cls._document(*columns))
        tsquery = func.websearch_to_tsquery("simple", query)
        trigram = or_(*(column.ilike(f"%{query}%") for column in columns))
        return or_(vector.op("@@")(tsquery), trigram)

    @classmethod
    def _score(cls, *columns, query: str):
        vector = func.to_tsvector("simple", cls._document(*columns))
        tsquery = func.websearch_to_tsquery("simple", query)
        similarities = [func.similarity(func.coalesce(column, ""), query) for column in columns]
        return (
            func.ts_rank_cd(vector, tsquery) * 2 + func.greatest(*similarities)
        ).label("score")

    async def dialogs(self, owner_user_id: int, query: str, limit: int, filters: SearchFilters):
        columns = (Dialog.peer_name, Dialog.peer_username)
        score = self._score(*columns, query=query)
        statement = select(Dialog, score).where(
            Dialog.owner_user_id == owner_user_id,
            self._matches(*columns, query=query),
        )
        if filters.dialog_id is not None:
            statement = statement.where(Dialog.id == filters.dialog_id)
        if filters.date_from is not None:
            statement = statement.where(Dialog.last_message_at >= filters.date_from)
        if filters.date_to is not None:
            statement = statement.where(Dialog.last_message_at <= filters.date_to)
        if filters.cursor is not None:
            statement = statement.where(Dialog.last_message_at < filters.cursor)
        return list((await self._session.execute(
            statement.order_by(desc(score), desc(Dialog.last_message_at), desc(Dialog.id)).limit(limit)
        )).all())

    async def messages(self, owner_user_id: int, query: str, limit: int, filters: SearchFilters):
        columns = (Message.text, Message.caption)
        score = self._score(*columns, query=query)
        statement = (
            select(Message, Dialog, score)
            .join(Dialog, Dialog.id == Message.dialog_id)
            .where(Dialog.owner_user_id == owner_user_id, self._matches(*columns, query=query))
        )
        if filters.dialog_id is not None:
            statement = statement.where(Dialog.id == filters.dialog_id)
        if filters.date_from is not None:
            statement = statement.where(Message.sent_at >= filters.date_from)
        if filters.date_to is not None:
            statement = statement.where(Message.sent_at <= filters.date_to)
        if filters.cursor is not None:
            statement = statement.where(Message.sent_at < filters.cursor)
        return list((await self._session.execute(
            statement.order_by(desc(score), desc(Message.sent_at), desc(Message.id)).limit(limit)
        )).all())

    async def versions(self, owner_user_id: int, query: str, limit: int, filters: SearchFilters):
        columns = (MessageVersion.text, MessageVersion.caption)
        score = self._score(*columns, query=query)
        statement = (
            select(MessageVersion, Message, Dialog, score)
            .join(Message, Message.id == MessageVersion.message_id)
            .join(Dialog, Dialog.id == Message.dialog_id)
            .where(Dialog.owner_user_id == owner_user_id, self._matches(*columns, query=query))
        )
        if filters.dialog_id is not None:
            statement = statement.where(Dialog.id == filters.dialog_id)
        if filters.date_from is not None:
            statement = statement.where(MessageVersion.created_at >= filters.date_from)
        if filters.date_to is not None:
            statement = statement.where(MessageVersion.created_at <= filters.date_to)
        if filters.cursor is not None:
            statement = statement.where(MessageVersion.created_at < filters.cursor)
        return list((await self._session.execute(
            statement.order_by(
                desc(score), desc(MessageVersion.created_at), desc(MessageVersion.id)
            ).limit(limit)
        )).all())

    async def media(self, owner_user_id: int, query: str, limit: int, filters: SearchFilters):
        columns = (Media.filename, Media.mime_type, Media.media_type)
        score = self._score(*columns, query=query)
        statement = (
            select(Media, Message, Dialog, score)
            .join(Message, Message.id == Media.message_id)
            .join(Dialog, Dialog.id == Message.dialog_id)
            .where(Dialog.owner_user_id == owner_user_id, self._matches(*columns, query=query))
        )
        if filters.dialog_id is not None:
            statement = statement.where(Dialog.id == filters.dialog_id)
        if filters.date_from is not None:
            statement = statement.where(Message.sent_at >= filters.date_from)
        if filters.date_to is not None:
            statement = statement.where(Message.sent_at <= filters.date_to)
        if filters.cursor is not None:
            statement = statement.where(Message.sent_at < filters.cursor)
        return list((await self._session.execute(
            statement.order_by(desc(score), desc(Message.sent_at), desc(Media.id)).limit(limit)
        )).all())
