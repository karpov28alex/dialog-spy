from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUser, SessionDep
from app.api.routes.user import require_archive_access
from app.core.config import Settings, get_settings
from app.modules.archive.repository import ArchiveRepository
from app.modules.archive.schemas import DialogListResponse
from app.modules.archive.service import ArchiveService

router = APIRouter(prefix="/api/v2/archive", tags=["archive-v2"])


@router.get("/dialogs", response_model=DialogListResponse)
async def list_dialogs(
    user: CurrentUser,
    session: SessionDep,
    limit: int = Query(30, ge=1, le=100),
    cursor: int | None = None,
    settings: Settings = Depends(get_settings),
) -> DialogListResponse:
    await require_archive_access(user, session)
    service = ArchiveService(ArchiveRepository(session), settings)
    return await service.list_dialogs(
        owner_user_id=user.id,
        limit=limit,
        cursor=cursor,
    )
