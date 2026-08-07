from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DialogListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    peer_name: str | None
    peer_username: str | None
    avatar: str | None
    message_count: int
    edited_count: int = 0
    deleted_count: int = 0
    media_count: int = 0
    protected_media_count: int = 0
    last_message_at: datetime | None
    last_message_text: str | None
    last_message_deleted: bool
    last_message_edited: bool
    direction: str | None
    is_hidden: bool


class DialogListResponse(BaseModel):
    items: list[DialogListItem]
    next_cursor: int | None


class MediaItem(BaseModel):
    id: int
    type: str
    is_protected: bool
    status: str
    mime_type: str | None
    filename: str | None
    size: int | None
    url: str | None


class MessageVersionItem(BaseModel):
    version: int
    text: str | None
    caption: str | None
    created_at: datetime


class MessageItem(BaseModel):
    id: int
    direction: str
    text: str | None
    caption: str | None
    sent_at: datetime
    edited_at: datetime | None
    deleted_at: datetime | None
    is_deleted: bool
    reply_to_message_id: int | None
    media: list[MediaItem]
    versions: list[MessageVersionItem]


class DialogSummary(BaseModel):
    id: int
    peer_name: str | None
    peer_username: str | None
    avatar: str | None


class DialogMetrics(BaseModel):
    message_count: int = 0
    edited_count: int = 0
    deleted_count: int = 0
    media_count: int = 0
    protected_media_count: int = 0


class DialogDetailResponse(BaseModel):
    dialog: DialogSummary
    metrics: DialogMetrics
    messages: list[MessageItem]
    next_cursor: int | None


class DialogPatch(BaseModel):
    is_hidden: bool | None = None
    is_muted: bool | None = None


class OperationResponse(BaseModel):
    ok: bool = True


class MessageVersionsResponse(BaseModel):
    items: list[MessageVersionItem]
    current: dict[str, str | datetime | None]
