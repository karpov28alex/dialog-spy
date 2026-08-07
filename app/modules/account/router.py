from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import CurrentUser, SessionDep
from app.bot.setup import bot
from app.core.config import Settings, get_settings
from app.modules.account.schemas import (
    ProfileResponse,
    SettingsPatch,
    SettingsPatchResponse,
    SubscriptionResponse,
    UserSettingsResponse,
)
from app.modules.account.service import AccountService, commerce_visible
from app.services.access_funnel import channel_gate_passed, get_funnel_config

router = APIRouter(tags=["account"])
SettingsDep = Annotated[Settings, Depends(get_settings)]


async def require_channel_access(user: CurrentUser) -> None:
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


def service(session: SessionDep, settings: SettingsDep) -> AccountService:
    return AccountService(session, bot, settings.telegram_bot_username)


@router.get("/ui-config")
async def ui_config() -> dict[str, bool]:
    return {"commerce_visible": await commerce_visible()}


@router.get("/me", response_model=ProfileResponse)
async def me(
    user: CurrentUser,
    session: SessionDep,
    settings: SettingsDep,
) -> ProfileResponse:
    return await service(session, settings).profile(user)


@router.get("/subscription", response_model=SubscriptionResponse)
async def subscription(
    user: CurrentUser,
    session: SessionDep,
    settings: SettingsDep,
) -> SubscriptionResponse:
    await require_channel_access(user)
    return await service(session, settings).subscription(user)


@router.get("/settings", response_model=UserSettingsResponse)
async def get_settings_route(user: CurrentUser) -> UserSettingsResponse:
    return AccountService.settings(user)


@router.patch("/settings", response_model=SettingsPatchResponse)
async def patch_settings(
    body: SettingsPatch,
    user: CurrentUser,
    session: SessionDep,
    settings: SettingsDep,
) -> SettingsPatchResponse:
    result = await service(session, settings).patch_settings(user, body)
    return SettingsPatchResponse(settings=result)
