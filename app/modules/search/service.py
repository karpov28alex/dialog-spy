from app.modules.search.repository import SearchRepository
from app.modules.search.schemas import SearchCounts, SearchItem, SearchResponse


def _snippet(*values: str | None, limit: int = 220) -> str:
    text = next((value.strip() for value in values if value and value.strip()), "")
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


class SearchService:
    def __init__(self, repository: SearchRepository) -> None:
        self._repository = repository

    async def search(self, *, owner_user_id: int, query: str, limit: int) -> SearchResponse:
        term = query.strip()
        pattern = f"%{term}%"
        dialogs = await self._repository.dialogs(owner_user_id, pattern, limit)
        messages = await self._repository.messages(owner_user_id, pattern, limit)
        versions = await self._repository.versions(owner_user_id, pattern, limit)
        media = await self._repository.media(owner_user_id, pattern, limit)

        items: list[SearchItem] = []
        for dialog in dialogs:
            items.append(SearchItem(kind="dialog", dialog_id=dialog.id, message_id=None,
                title=dialog.peer_name or dialog.peer_username or "Диалог",
                subtitle=f"@{dialog.peer_username}" if dialog.peer_username else "Диалог",
                snippet="Открыть переписку", at=dialog.last_message_at, media_type=None,
                edited=False, deleted=False))
        for message, dialog in messages:
            items.append(SearchItem(kind="message", dialog_id=dialog.id, message_id=message.id,
                title=dialog.peer_name or dialog.peer_username or "Диалог", subtitle="Сообщение",
                snippet=_snippet(message.text, message.caption), at=message.sent_at, media_type=None,
                edited=message.edited_at is not None, deleted=message.is_deleted))
        for version, message, dialog in versions:
            items.append(SearchItem(kind="version", dialog_id=dialog.id, message_id=message.id,
                title=dialog.peer_name or dialog.peer_username or "Диалог",
                subtitle=f"Версия {version.version_number}", snippet=_snippet(version.text, version.caption),
                at=version.created_at, media_type=None, edited=True, deleted=message.is_deleted))
        for item, message, dialog in media:
            items.append(SearchItem(kind="media", dialog_id=dialog.id, message_id=message.id,
                title=dialog.peer_name or dialog.peer_username or "Диалог",
                subtitle=item.filename or item.media_type,
                snippet=_snippet(message.text, message.caption, item.mime_type, item.media_type),
                at=message.sent_at, media_type=item.media_type,
                edited=message.edited_at is not None, deleted=message.is_deleted))

        items.sort(key=lambda item: item.at.timestamp() if item.at else 0, reverse=True)
        return SearchResponse(
            query=term,
            items=items[:limit],
            counts=SearchCounts(
                dialogs=len(dialogs), messages=len(messages), versions=len(versions), media=len(media)
            ),
        )
