from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse

from app.api.deps import CurrentUser, SessionDep
from app.core.config import Settings, get_settings
from app.modules.archive.access import require_archive_access
from app.modules.archive.repository import ArchiveRepository
from app.modules.archive.router import download_media as download_media_v2
from app.modules.archive.schemas import DialogPatch
from app.modules.archive.service import ArchiveService

router = APIRouter(prefix="/api", tags=["archive-legacy"])


def archive_service(session: SessionDep, settings: Settings) -> ArchiveService:
    return ArchiveService(ArchiveRepository(session), settings)


@router.get("/dialogs")
async def dialogs(
    user: CurrentUser,
    session: SessionDep,
    limit: int = Query(30, ge=1, le=100),
    cursor: int | None = None,
    settings: Settings = Depends(get_settings),
) -> dict:
    await require_archive_access(user, session)
    response = await archive_service(session, settings).list_dialogs(
        owner_user_id=user.id,
        limit=limit,
        cursor=cursor,
    )
    return response.model_dump()


@router.get("/dialogs/{dialog_id}")
async def dialog_detail(
    dialog_id: int,
    user: CurrentUser,
    session: SessionDep,
    limit: int = Query(50, ge=1, le=100),
    before_id: int | None = None,
    settings: Settings = Depends(get_settings),
) -> dict:
    await require_archive_access(user, session)
    response = await archive_service(session, settings).dialog_detail(
        owner_user_id=user.id,
        dialog_id=dialog_id,
        limit=limit,
        before_id=before_id,
    )
    payload = response.model_dump()
    for message in payload["messages"]:
        for media in message["media"]:
            if media["url"]:
                media["url"] = media["url"].replace(
                    "/api/v2/archive/media/download/",
                    "/api/media/download/",
                    1,
                )
    return payload


@router.patch("/dialogs/{dialog_id}")
async def patch_dialog(
    dialog_id: int,
    body: DialogPatch,
    user: CurrentUser,
    session: SessionDep,
    settings: Settings = Depends(get_settings),
) -> dict:
    await require_archive_access(user, session)
    response = await archive_service(session, settings).patch_dialog(
        owner_user_id=user.id,
        dialog_id=dialog_id,
        patch=body,
    )
    return response.model_dump()


@router.get("/messages/{message_id}/versions")
async def versions(
    message_id: int,
    user: CurrentUser,
    session: SessionDep,
    settings: Settings = Depends(get_settings),
) -> dict:
    await require_archive_access(user, session)
    response = await archive_service(session, settings).message_versions(
        owner_user_id=user.id,
        message_id=message_id,
    )
    return response.model_dump()


@router.get("/media/download/{token}", include_in_schema=False)
async def download_media(
    token: str,
    session: SessionDep,
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    return await download_media_v2(token=token, session=session, settings=settings)
