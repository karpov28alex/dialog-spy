from app.modules.search.repository import SearchRepository
from app.modules.search.schemas import (
    SearchCounts,
    SearchFilters,
    SearchItem,
    SearchKind,
    SearchResponse,
)


def _snippet(*values: str | None, limit: int = 220) -> str:
    text = next((value.strip() for value in values if value and value.strip()), "")
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


class SearchService:
    def __init__(self, repository: SearchRepository) -> None:
        self._repository = repository

    async def search(
        self,
        *,
        owner_user_id: int,
        query: str,
        limit: int,
        filters: SearchFilters | None = None,
    ) -> SearchResponse:
        term = query.strip()
        active_filters = filters or SearchFilters()
        selected: set[SearchKind] = set(
            active_filters.kinds or ["dialog", "message", "version", "media"]
        )
        fetch_limit = limit + 1

        dialogs = (
            await self._repository.dialogs(owner_user_id, term, fetch_limit, active_filters)
            if "dialog" in selected
            else []
        )
        messages = (
            await self._repository.messages(owner_user_id, term, fetch_limit, active_filters)
            if "message" in selected
            else []
        )
        versions = (
            await self._repository.versions(owner_user_id, term, fetch_limit, active_filters)
            if "version" in selected
            else []
        )
        media = (
            await self._repository.media(owner_user_id, term, fetch_limit, active_filters)
            if "media" in selected
            else []
        )

        items: list[SearchItem] = []
        for dialog, score in dialogs:
            items.append(
                SearchItem(
                    kind="dialog",
                    dialog_id=dialog.id,
                    message_id=None,
                    title=dialog.peer_name or dialog.peer_username or "Диалог",
                    subtitle=f"@{dialog.peer_username}" if dialog.peer_username else "Диалог",
                    snippet="Открыть переписку",
                    at=dialog.last_message_at,
                    media_type=None,
                    edited=False,
                    deleted=False,
                    score=float(score or 0),
                )
            )
        for message, dialog, score in messages:
            items.append(
                SearchItem(
                    kind="message",
                    dialog_id=dialog.id,
                    message_id=message.id,
                    title=dialog.peer_name or dialog.peer_username or "Диалог",
                    subtitle="Сообщение",
                    snippet=_snippet(message.text, message.caption),
                    at=message.sent_at,
                    media_type=None,
                    edited=message.edited_at is not None,
                    deleted=message.is_deleted,
                    score=float(score or 0),
                )
            )
        for version, message, dialog, score in versions:
            items.append(
                SearchItem(
                    kind="version",
                    dialog_id=dialog.id,
                    message_id=message.id,
                    title=dialog.peer_name or dialog.peer_username or "Диалог",
                    subtitle=f"Версия {version.version_number}",
                    snippet=_snippet(version.text, version.caption),
                    at=version.created_at,
                    media_type=None,
                    edited=True,
                    deleted=message.is_deleted,
                    score=float(score or 0),
                )
            )
        for media_item, message, dialog, score in media:
            items.append(
                SearchItem(
                    kind="media",
                    dialog_id=dialog.id,
                    message_id=message.id,
                    title=dialog.peer_name or dialog.peer_username or "Диалог",
                    subtitle=media_item.filename or media_item.media_type,
                    snippet=_snippet(
                        message.text,
                        message.caption,
                        media_item.mime_type,
                        media_item.media_type,
                    ),
                    at=message.sent_at,
                    media_type=media_item.media_type,
                    edited=message.edited_at is not None,
                    deleted=message.is_deleted,
                    score=float(score or 0),
                )
            )

        items.sort(
            key=lambda item: (
                item.score,
                item.at.timestamp() if item.at else 0,
                item.message_id or item.dialog_id,
            ),
            reverse=True,
        )
        page = items[:limit]
        next_cursor = page[-1].at if len(items) > limit and page else None
        return SearchResponse(
            query=term,
            items=page,
            counts=SearchCounts(
                dialogs=len(dialogs),
                messages=len(messages),
                versions=len(versions),
                media=len(media),
            ),
            next_cursor=next_cursor,
        )
