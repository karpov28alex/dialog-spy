from datetime import timedelta

from fastapi import HTTPException

from app.core.config import Settings
from app.core.security import create_token
from app.modules.archive.repository import ArchiveRepository
from app.modules.archive.schemas import (
    DialogDetailResponse,
    DialogListItem,
    DialogListResponse,
    DialogPatch,
    DialogSummary,
    MediaItem,
    MessageItem,
    MessageVersionItem,
    MessageVersionsResponse,
    OperationResponse,
)


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

    def _media_url(self, user_id: int, media_id: int) -> str:
        token = create_token(
            f"{user_id}:{media_id}",
            "media_download",
            timedelta(seconds=self._settings.media_signing_ttl_seconds),
            self._settings,
        )
        return f"/api/v2/archive/media/download/{token}"

    async def list_dialogs(
        self, *, owner_user_id: int, limit: int, cursor: int | None
    ) -> DialogListResponse:
        rows = await self._repository.list_dialogs(
            owner_user_id=owner_user_id, limit=limit, cursor=cursor
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
                    avatar=self._avatar_url(owner_user_id, dialog.id)
                    if dialog.peer_telegram_id
                    else None,
                    message_count=await self._repository.message_count(dialog.id),
                    last_message_at=dialog.last_message_at,
                    last_message_text=(last_message.text or last_message.caption)
                    if last_message
                    else None,
                    last_message_deleted=bool(last_message and last_message.is_deleted),
                    last_message_edited=bool(last_message and last_message.edited_at),
                    direction=last_message.direction if last_message else None,
                    is_hidden=dialog.is_hidden,
                )
            )
        return DialogListResponse(items=items, next_cursor=next_cursor)

    async def dialog_detail(
        self,
        *,
        owner_user_id: int,
        dialog_id: int,
        limit: int,
        before_id: int | None,
    ) -> DialogDetailResponse:
        dialog = await self._repository.get_dialog(
            dialog_id=dialog_id, owner_user_id=owner_user_id
        )
        if dialog is None:
            raise HTTPException(status_code=404, detail="Dialog not found")

        rows = await self._repository.list_messages(
            dialog_id=dialog.id, limit=limit, before_id=before_id
        )
        next_cursor = rows[-1].id if len(rows) > limit else None
        page = rows[:limit]
        message_ids = [message.id for message in page]
        media_rows = await self._repository.media_for_messages(message_ids)
        version_rows = await self._repository.versions_for_messages(message_ids)

        media_by_message: dict[int, list[MediaItem]] = {}
        for media in media_rows:
            url = None
            if media.download_status == "downloaded" and media.storage_key:
                url = self._media_url(owner_user_id, media.id)
            media_by_message.setdefault(media.message_id, []).append(
                MediaItem(
                    id=media.id,
                    type=media.media_type,
                    is_protected=media.is_protected,
                    status=media.download_status,
                    mime_type=media.mime_type,
                    filename=media.filename,
                    size=media.size,
                    url=url,
                )
            )

        versions_by_message: dict[int, list[MessageVersionItem]] = {}
        for version in version_rows:
            versions_by_message.setdefault(version.message_id, []).append(
                MessageVersionItem(
                    version=version.version_number,
                    text=version.text,
                    caption=version.caption,
                    created_at=version.created_at,
                )
            )

        messages = [
            MessageItem(
                id=message.id,
                direction=message.direction,
                text=message.text,
                caption=message.caption,
                sent_at=message.sent_at,
                edited_at=message.edited_at,
                deleted_at=message.deleted_at,
                is_deleted=message.is_deleted,
                reply_to_message_id=message.reply_to_message_id,
                media=media_by_message.get(message.id, []),
                versions=versions_by_message.get(message.id, []),
            )
            for message in reversed(page)
        ]
        return DialogDetailResponse(
            dialog=DialogSummary(
                id=dialog.id,
                peer_name=dialog.peer_name,
                peer_username=dialog.peer_username,
                avatar=self._avatar_url(owner_user_id, dialog.id)
                if dialog.peer_telegram_id
                else None,
            ),
            messages=messages,
            next_cursor=next_cursor,
        )

    async def patch_dialog(
        self, *, owner_user_id: int, dialog_id: int, patch: DialogPatch
    ) -> OperationResponse:
        dialog = await self._repository.get_dialog(
            dialog_id=dialog_id, owner_user_id=owner_user_id
        )
        if dialog is None:
            raise HTTPException(status_code=404, detail="Dialog not found")
        for key, value in patch.model_dump(exclude_none=True).items():
            setattr(dialog, key, value)
        await self._repository.commit()
        return OperationResponse()

    async def message_versions(
        self, *, owner_user_id: int, message_id: int
    ) -> MessageVersionsResponse:
        message = await self._repository.get_message(
            message_id=message_id, owner_user_id=owner_user_id
        )
        if message is None:
            raise HTTPException(status_code=404, detail="Message not found")
        rows = await self._repository.versions_for_message(message.id)
        return MessageVersionsResponse(
            items=[
                MessageVersionItem(
                    version=row.version_number,
                    text=row.text,
                    caption=row.caption,
                    created_at=row.created_at,
                )
                for row in rows
            ],
            current={
                "text": message.text,
                "caption": message.caption,
                "edited_at": message.edited_at,
            },
        )
