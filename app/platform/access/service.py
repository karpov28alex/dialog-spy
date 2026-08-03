from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.platform.access.domain import AccessDecision, decision_from_access_center
from app.services.access_center import build_access_center


class AccessPlatformService:
    """Compatibility-safe entry point for the Platform 3.0 access domain."""

    async def evaluate_with_center(
        self,
        *,
        session: AsyncSession,
        user: User,
        bot,
    ) -> tuple[AccessDecision, dict[str, Any]]:
        center = await build_access_center(session=session, user=user, bot=bot)
        return decision_from_access_center(center), center

    async def evaluate(self, *, session: AsyncSession, user: User, bot) -> AccessDecision:
        decision, _ = await self.evaluate_with_center(session=session, user=user, bot=bot)
        return decision

    async def payload(self, *, session: AsyncSession, user: User, bot) -> dict[str, Any]:
        decision, center = await self.evaluate_with_center(session=session, user=user, bot=bot)
        return {**decision.as_dict(), "center": center}
