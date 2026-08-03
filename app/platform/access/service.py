from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.platform.access.domain import AccessDecision, decision_from_access_center
from app.services.access_center import build_access_center


class AccessPlatformService:
    """Compatibility-safe entry point for the Platform 3.0 access domain."""

    async def evaluate(self, *, session: AsyncSession, user: User, bot) -> AccessDecision:
        center = await build_access_center(session=session, user=user, bot=bot)
        return decision_from_access_center(center)
