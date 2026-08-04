from datetime import datetime

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, SessionDep
from app.modules.search.repository import SearchRepository
from app.modules.search.schemas import SearchFilters, SearchKind, SearchResponse
from app.modules.search.service import SearchService

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("", response_model=SearchResponse)
async def global_search(
    user: CurrentUser,
    session: SessionDep,
    q: str = Query(min_length=2, max_length=160),
    limit: int = Query(40, ge=1, le=100),
    kinds: list[SearchKind] | None = Query(default=None),
    dialog_id: int | None = Query(default=None, ge=1),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    cursor: datetime | None = None,
) -> SearchResponse:
    return await SearchService(SearchRepository(session)).search(
        owner_user_id=user.id,
        query=q,
        limit=limit,
        filters=SearchFilters(
            kinds=kinds,
            dialog_id=dialog_id,
            date_from=date_from,
            date_to=date_to,
            cursor=cursor,
        ),
    )
