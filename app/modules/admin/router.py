import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import decode_token
from app.db.session import get_session
from app.modules.admin.schemas import AdminDashboardResponse
from app.modules.admin.service import AdminDashboardService

router = APIRouter(prefix="/v2/admin", tags=["admin-v2"])
SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def admin_guard(
    settings: SettingsDep,
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )
    try:
        subject = decode_token(
            authorization.removeprefix("Bearer "),
            "admin_access",
            settings,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        ) from exc
    if not hmac.compare_digest(subject, settings.admin_email):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )
    return subject


AdminAuth = Annotated[str, Depends(admin_guard)]


@router.get("/dashboard", response_model=AdminDashboardResponse)
async def dashboard(_: AdminAuth, session: SessionDep) -> AdminDashboardResponse:
    return await AdminDashboardService(session).dashboard()
