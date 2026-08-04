from datetime import timedelta

from app.core.config import Settings
from app.core.security import create_token
from app.modules.archive.repository import ArchiveRepository
from app.modules.archive.schemas import DialogListItem, DialogListResponse


class ArchiveService:
    def __init__(self, repository: ArchiveRepository, settings: Settings) -> None:
        self._repository = repository
        self._settings = settings

    def _avatar_url(self, user_id: int, dialog_id: int) -> str:
        token = create_token(
            f"{user_id}:{dialog_id}",
            "dialog_avatar",
            timedelta(minutes=15),
            self._settings,
        )
        return f"/api/avatar/{token}"

    async def list_dialogs(
        self,
        *,
        owner_user_id: int,
        limit: int,
        cursor: int | None,
    ) -> DialogListResponse:
        rows = await self._repository.list_dialogs(
            owner_user_id=owner_user_id,
            limit=limit,
            cursor=cursor,
        )
        next_cursor = rows[-1].id if len(rows) > limit else None
        items: list[DialogListItem] = []
        for dialog in rows[:limit]:
            last_message = await self._repository.last_message(dialog.id)
            items.append(
                DialogListItem(
                    id=dialog.id,
                    peer_name=dialog.peer_name,
                    peer_username=dialog.peer_username,
                    avatar=(
                        self._avatar_url(owner_user_id, dialog.id)
                        if dialog.peer_telegram_id
                        else None
                    ),
                    message_count=await self._repository.message_count(dialog.id),
                    last_message_at=dialog.last_message_at,
                    last_message_text=(
                        (last_message.text or last_message.caption) if last_message else None
                    ),
                    last_message_deleted=bool(last_message and last_message.is_deleted),
                    last_message_edited=bool(last_message and last_message.edited_at),
                    direction=last_message.direction if last_message else None,
                    is_hidden=dialog.is_hidden,
                )
            )
        return DialogListResponse(items=items, next_cursor=next_cursor)
