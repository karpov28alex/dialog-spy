from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import CurrentUser, SessionDep
from app.bot.setup import bot
from app.core.config import Settings, get_settings
from app.db.models import BusinessConnection, User
from app.modules.archive.legacy_router import router as legacy_archive_router
from app.services.access import access_state, get_monetization_settings, payment_plans
from app.services.access_funnel import channel_gate_passed, get_funnel_config
from app.services.users import referral_code

router = APIRouter(prefix="/api", tags=["user"])
router.include_router(legacy_archive_router)


async def require_channel_access(user: User) -> None:
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


@router.get("/me")
async def me(
    user: CurrentUser,
    session: SessionDep,
    settings: Settings = Depends(get_settings),
) -> dict:
    connection = await session.scalar(
        select(BusinessConnection).where(
            BusinessConnection.owner_user_id == user.id,
            BusinessConnection.is_active.is_(True),
        )
    )
    config = await get_monetization_settings(session)
    funnel = await get_funnel_config()
    access = await access_state(session, user)
    verified = (
        await channel_gate_passed(bot, user_id=user.telegram_id, config=funnel)
        if funnel.enabled
        else True
    )
    referral_link = (
        f"https://t.me/{settings.telegram_bot_username}?start=ref_{referral_code(user)}"
    )
    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "business_connected": bool(connection),
        "access": {
            "active": access.active,
            "source": access.source,
            "ends_at": access.ends_at,
            "needs_payment": access.needs_payment,
        },
        "funnel": {
            "enabled": funnel.enabled,
            "channel_required": True,
            "channel_verified": verified,
            "channel_title": funnel.channel_title,
            "channel_url": funnel.channel_url,
            "subscription_text": funnel.subscription_text,
            "referral_required": funnel.referral_required,
            "referral_text": funnel.referral_text,
            "payment_required_text": funnel.payment_required_text,
            "payment_button_text": funnel.payment_button_text,
            "payment_url": funnel.payment_url,
        },
        "monetization": {
            "free_trial_enabled": config.free_trial_enabled,
            "show_trial_in_profile": config.show_trial_in_profile,
            "show_tariffs": config.show_tariffs,
            "referral_available": user.referral_bonus_granted_at is None,
            "referral_link": referral_link,
            "payment_url": funnel.payment_url or config.payment_placeholder_url,
            "plans": payment_plans(config) if config.show_tariffs else [],
            "demo": True,
        },
    }


@router.get("/subscription")
async def subscription(
    user: CurrentUser,
    session: SessionDep,
    settings: Settings = Depends(get_settings),
) -> dict:
    await require_channel_access(user)
    config = await get_monetization_settings(session)
    funnel = await get_funnel_config()
    access = await access_state(session, user)
    return {
        "access": {
            "active": access.active,
            "source": access.source,
            "ends_at": access.ends_at,
        },
        "plans": payment_plans(config) if config.show_tariffs else [],
        "payment_url": funnel.payment_url or config.payment_placeholder_url,
        "payment_button_text": funnel.payment_button_text,
        "referral_link": (
            f"https://t.me/{settings.telegram_bot_username}?start=ref_{referral_code(user)}"
        ),
        "referral_available": user.referral_bonus_granted_at is None,
        "demo": True,
    }


SETTINGS_FIELDS = (
    "notifications_enabled",
    "save_protected_media",
    "notify_edits",
    "notify_deletions",
    "notify_protected_media",
    "notify_connection",
    "hide_preview",
    "notify_emoji",
    "theme",
    "language",
    "timezone",
)


@router.get("/settings")
async def get_settings_route(user: CurrentUser) -> dict:
    return {key: getattr(user.settings, key) for key in SETTINGS_FIELDS}


class SettingsPatch(BaseModel):
    notifications_enabled: bool | None = None
    save_protected_media: bool | None = None
    notify_edits: bool | None = None
    notify_deletions: bool | None = None
    notify_protected_media: bool | None = None
    notify_connection: bool | None = None
    hide_preview: bool | None = None
    notify_emoji: bool | None = None
    theme: str | None = Field(default=None, pattern="^(dark|light|system)$")
    language: str | None = Field(default=None, max_length=16)
    timezone: str | None = Field(default=None, max_length=64)


@router.patch("/settings")
async def patch_settings(
    body: SettingsPatch,
    user: CurrentUser,
    session: SessionDep,
) -> dict:
    values = body.model_dump(exclude_none=True)
    for key, value in values.items():
        setattr(user.settings, key, value)
    await session.commit()
    return {
        "ok": True,
        "settings": {key: getattr(user.settings, key) for key in SETTINGS_FIELDS},
    }
