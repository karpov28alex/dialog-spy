from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.setup import bot
from app.db.models import User
from app.services.access import access_state
from app.services.access_funnel import channel_gate_passed, get_funnel_config


async def require_archive_access(user: User, session: AsyncSession) -> None:
    funnel = await get_funnel_config()
    if funnel.enabled and not await channel_gate_passed(
        bot,
        user_id=user.telegram_id,
        config=funnel,
    ):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "CHANNEL_SUBSCRIPTION_REQUIRED",
                "message": funnel.subscription_text,
                "channel_url": funnel.channel_url,
                "channel_title": funnel.channel_title,
            },
        )

    access = await access_state(session, user)
    if funnel.enabled and not access.active:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "PAYMENT_REQUIRED",
                "message": (
                    funnel.referral_text
                    if user.referral_bonus_granted_at is None
                    else funnel.payment_required_text
                ),
                "payment_url": funnel.payment_url,
                "payment_button_text": funnel.payment_button_text,
                "referral_available": user.referral_bonus_granted_at is None,
            },
        )
