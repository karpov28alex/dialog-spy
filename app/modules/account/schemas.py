from datetime import datetime

from pydantic import BaseModel, Field


class AccessSummary(BaseModel):
    active: bool
    source: str
    ends_at: datetime | None
    needs_payment: bool = False


class FunnelSummary(BaseModel):
    enabled: bool
    channel_required: bool
    channel_verified: bool
    channel_title: str
    channel_url: str
    subscription_text: str
    referral_required: bool
    referral_text: str
    payment_required_text: str
    payment_button_text: str
    payment_url: str


class MonetizationSummary(BaseModel):
    free_trial_enabled: bool
    show_trial_in_profile: bool
    show_tariffs: bool
    commerce_visible: bool = True
    referral_available: bool
    referral_link: str
    payment_url: str
    plans: list[dict]
    demo: bool = True


class ProfileResponse(BaseModel):
    id: int
    telegram_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    business_connected: bool
    access: AccessSummary
    funnel: FunnelSummary
    monetization: MonetizationSummary


class SubscriptionResponse(BaseModel):
    access: AccessSummary
    plans: list[dict]
    payment_url: str
    payment_button_text: str
    referral_link: str
    referral_available: bool
    demo: bool = True


class UserSettingsResponse(BaseModel):
    notifications_enabled: bool
    save_protected_media: bool
    notify_edits: bool
    notify_deletions: bool
    notify_protected_media: bool
    notify_connection: bool
    hide_preview: bool
    notify_emoji: bool
    theme: str
    language: str
    timezone: str


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


class SettingsPatchResponse(BaseModel):
    ok: bool = True
    settings: UserSettingsResponse
