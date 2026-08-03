from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.bot.setup import bot
from app.platform.access.service import AccessPlatformService

router = APIRouter(prefix="/api/access-center", tags=["access-center"])
service = AccessPlatformService()


@router.get("")
async def access_center(user: CurrentUser, session: SessionDep) -> dict:
    """Return the access-center payload with the unified Platform decision."""
    decision, center = await service.evaluate_with_center(session=session, user=user, bot=bot)
    return {**center, "platform_access": decision.as_dict()}
