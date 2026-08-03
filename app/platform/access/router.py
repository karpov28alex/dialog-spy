from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.bot.setup import bot
from app.platform.access.service import AccessPlatformService

router = APIRouter(prefix="/api/v3/access", tags=["platform-access"])
service = AccessPlatformService()


@router.get("")
async def access_status(user: CurrentUser, session: SessionDep) -> dict:
    decision = await service.evaluate(session=session, user=user, bot=bot)
    return decision.as_dict()


@router.post("/recalculate")
async def recalculate_access(user: CurrentUser, session: SessionDep) -> dict:
    decision = await service.evaluate(session=session, user=user, bot=bot)
    return decision.as_dict()
