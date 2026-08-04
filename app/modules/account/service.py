from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BusinessConnection, User
from app.modules.account.schemas import (
    AccessSummary,
    FunnelSummary,
    MonetizationSummary,
    ProfileResponse,
    SettingsPatch,
    SubscriptionResponse,
    UserSettingsResponse,
)
from app.services.access import access_state, get_monetization_settings, payment_plans
from app.services.access_funnel import channel_gate_passed, get_funnel_config
from app.services.users import referral_code


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


class AccountService:
    def __init__(self, session: AsyncSession, bot, bot_username: str) -> None:
        self._session = session
        self._bot = bot
        self._bot_username = bot_username

    def referral_link(self, user: User) -> str:
        return f"https://t.me/{self._bot_username}?start=ref_{referral_code(user)}"

    async def channel_verified(self, user: User, funnel) -> bool:
        if not funnel.enabled:
            return True
        return await channel_gate_passed(
            self._bot,
            user_id=user.telegram_id,
            config=funnel,
        )

    async def profile(self, user: User) -> ProfileResponse:
        connection = await self._session.scalar(
            select(BusinessConnection).where(
                BusinessConnection.owner_user_id == user.id,
                BusinessConnection.is_active.is_(True),
            )
        )
        config = await get_monetization_settings(self._session)
        funnel = await get_funnel_config()
        state = await access_state(self._session, user)
        referral_link = self.referral_link(user)
        return ProfileResponse(
            id=user.id,
            telegram_id=user.telegram_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            business_connected=bool(connection),
            access=AccessSummary(
                active=state.active,
                source=state.source,
                ends_at=state.ends_at,
                needs_payment=state.needs_payment,
            ),
            funnel=FunnelSummary(
                enabled=funnel.enabled,
                channel_required=True,
                channel_verified=await self.channel_verified(user, funnel),
                channel_title=funnel.channel_title,
                channel_url=funnel.channel_url,
                subscription_text=funnel.subscription_text,
                referral_required=funnel.referral_required,
                referral_text=funnel.referral_text,
                payment_required_text=funnel.payment_required_text,
                payment_button_text=funnel.payment_button_text,
                payment_url=funnel.payment_url,
            ),
            monetization=MonetizationSummary(
                free_trial_enabled=config.free_trial_enabled,
                show_trial_in_profile=config.show_trial_in_profile,
                show_tariffs=config.show_tariffs,
                referral_available=user.referral_bonus_granted_at is None,
                referral_link=referral_link,
                payment_url=funnel.payment_url or config.payment_placeholder_url,
                plans=payment_plans(config) if config.show_tariffs else [],
            ),
        )

    async def subscription(self, user: User) -> SubscriptionResponse:
        config = await get_monetization_settings(self._session)
        funnel = await get_funnel_config()
        state = await access_state(self._session, user)
        return SubscriptionResponse(
            access=AccessSummary(
                active=state.active,
                source=state.source,
                ends_at=state.ends_at,
                needs_payment=state.needs_payment,
            ),
            plans=payment_plans(config) if config.show_tariffs else [],
            payment_url=funnel.payment_url or config.payment_placeholder_url,
            payment_button_text=funnel.payment_button_text,
            referral_link=self.referral_link(user),
            referral_available=user.referral_bonus_granted_at is None,
        )

    @staticmethod
    def settings(user: User) -> UserSettingsResponse:
        return UserSettingsResponse(
            **{key: getattr(user.settings, key) for key in SETTINGS_FIELDS}
        )

    async def patch_settings(
        self,
        user: User,
        body: SettingsPatch,
    ) -> UserSettingsResponse:
        for key, value in body.model_dump(exclude_none=True).items():
            setattr(user.settings, key, value)
        await self._session.commit()
        return self.settings(user)
