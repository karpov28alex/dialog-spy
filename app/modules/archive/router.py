from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.api.deps import CurrentUser, SessionDep
from app.core.config import Settings, get_settings
from app.core.security import decode_token
from app.db.models import Dialog, Media, Message, User
from app.modules.archive.access import require_archive_access
from app.modules.archive.repository import ArchiveRepository
from app.modules.archive.schemas import (
    DialogDetailResponse,
    DialogListResponse,
    DialogPatch,
    MessageVersionsResponse,
    OperationResponse,
)
from app.modules.archive.service import ArchiveService
from app.services.media import safe_media_path

router = APIRouter(prefix="/api/v2/archive", tags=["archive-v2"])


def archive_service(session: SessionDep, settings: Settings) -> ArchiveService:
    return ArchiveService(ArchiveRepository(session), settings)


@router.get("/dialogs", response_model=DialogListResponse)
async def list_dialogs(
    user: CurrentUser,
    session: SessionDep,
    limit: int = Query(30, ge=1, le=100),
    cursor: int | None = None,
    settings: Settings = Depends(get_settings),
) -> DialogListResponse:
    await require_archive_access(user, session)
    return await archive_service(session, settings).list_dialogs(
        owner_user_id=user.id,
        limit=limit,
        cursor=cursor,
    )


@router.get("/dialogs/{dialog_id}", response_model=DialogDetailResponse)
async def dialog_detail(
    dialog_id: int,
    user: CurrentUser,
    session: SessionDep,
    limit: int = Query(50, ge=1, le=100),
    before_id: int | None = None,
    settings: Settings = Depends(get_settings),
) -> DialogDetailResponse:
    await require_archive_access(user, session)
    return await archive_service(session, settings).dialog_detail(
        owner_user_id=user.id,
        dialog_id=dialog_id,
        limit=limit,
        before_id=before_id,
    )


@router.patch("/dialogs/{dialog_id}", response_model=OperationResponse)
async def patch_dialog(
    dialog_id: int,
    body: DialogPatch,
    user: CurrentUser,
    session: SessionDep,
    settings: Settings = Depends(get_settings),
) -> OperationResponse:
    await require_archive_access(user, session)
    return await archive_service(session, settings).patch_dialog(
        owner_user_id=user.id,
        dialog_id=dialog_id,
        patch=body,
    )


@router.get(
    "/messages/{message_id}/versions",
    response_model=MessageVersionsResponse,
)
async def message_versions(
    message_id: int,
    user: CurrentUser,
    session: SessionDep,
    settings: Settings = Depends(get_settings),
) -> MessageVersionsResponse:
    await require_archive_access(user, session)
    return await archive_service(session, settings).message_versions(
        owner_user_id=user.id,
        message_id=message_id,
    )


@router.get("/media/download/{token}", include_in_schema=False)
async def download_media(
    token: str,
    session: SessionDep,
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    try:
        subject = decode_token(token, "media_download", settings)
        user_id_text, media_id_text = subject.split(":", 1)
        user_id, media_id = int(user_id_text), int(media_id_text)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=403, detail="Invalid media token") from exc

    owner = await session.get(User, user_id)
    if owner is None:
        raise HTTPException(status_code=404, detail="User not found")
    await require_archive_access(owner, session)

    result = (
        await session.execute(
            select(Media, Message, Dialog)
            .join(Message, Message.id == Media.message_id)
            .join(Dialog, Dialog.id == Message.dialog_id)
            .where(Media.id == media_id, Dialog.owner_user_id == user_id)
        )
    ).first()
    if result is None:
        raise HTTPException(status_code=404, detail="Media not found")
    media, _, _ = result
    if media.download_status != "downloaded" or not media.storage_key:
        raise HTTPException(status_code=409, detail="Media is not ready")

    path = safe_media_path(settings, media.storage_key)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Media file missing")
    return FileResponse(
        path,
        media_type=media.mime_type or "application/octet-stream",
        filename=media.filename or f"media-{media.id}",
        headers={"Cache-Control": "private, no-store"},
    )
