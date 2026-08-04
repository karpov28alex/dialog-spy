from datetime import datetime
from typing import Literal

from pydantic import BaseModel

SearchKind = Literal["dialog", "message", "version", "media"]


class SearchFilters(BaseModel):
    kinds: list[SearchKind] | None = None
    dialog_id: int | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    cursor: datetime | None = None


class SearchItem(BaseModel):
    kind: SearchKind
    dialog_id: int
    message_id: int | None
    title: str
    subtitle: str
    snippet: str
    at: datetime | None
    media_type: str | None
    edited: bool
    deleted: bool
    score: float = 0.0


class SearchCounts(BaseModel):
    dialogs: int
    messages: int
    versions: int
    media: int


class SearchResponse(BaseModel):
    query: str
    items: list[SearchItem]
    counts: SearchCounts
    next_cursor: datetime | None = None
