from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DialogListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    peer_name: str | None
    peer_username: str | None
    avatar: str | None
    message_count: int
    last_message_at: datetime | None
    last_message_text: str | None
    last_message_deleted: bool
    last_message_edited: bool
    direction: str | None
    is_hidden: bool


class DialogListResponse(BaseModel):
    items: list[DialogListItem]
    next_cursor: int | None
