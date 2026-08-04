from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class SearchItem(BaseModel):
    kind: Literal["dialog", "message", "version", "media"]
    dialog_id: int
    message_id: int | None
    title: str
    subtitle: str
    snippet: str
    at: datetime | None
    media_type: str | None
    edited: bool
    deleted: bool


class SearchCounts(BaseModel):
    dialogs: int
    messages: int
    versions: int
    media: int


class SearchResponse(BaseModel):
    query: str
    items: list[SearchItem]
    counts: SearchCounts
