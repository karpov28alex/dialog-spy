from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any, Mapping


class AccessState(StrEnum):
    CHANNEL_REQUIRED = "channel_required"
    BUSINESS_REQUIRED = "business_required"
    TRIAL_ACTIVE = "trial_active"
    REFERRAL_REQUIRED = "referral_required"
    PAYMENT_REQUIRED = "payment_required"
    ACTIVE = "active"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class AccessDecision:
    allowed: bool
    state: AccessState
    title: str
    message: str
    next_step: str | None
    progress: int
    valid_until: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["state"] = self.state.value
        return payload


def decision_from_access_center(center: Mapping[str, Any]) -> AccessDecision:
    """Normalize the existing production access-center payload.

    The old service remains the source of external checks (Telegram channel,
    Business connection and monetization settings). Platform 3.0 consumes one
    stable decision object shared by future bot, Mini App and admin adapters.
    """

    stage = str(center.get("stage") or "payment")
    progress = max(0, min(100, int(center.get("progress") or 0)))
    next_action = str(center.get("next_action") or "")
    access = center.get("access") if isinstance(center.get("access"), Mapping) else {}

    if stage == "channel":
        return AccessDecision(
            allowed=False,
            state=AccessState.CHANNEL_REQUIRED,
            title="Подпишитесь на канал",
            message=next_action,
            next_step="verify_channel",
            progress=progress,
        )
    if stage == "business":
        return AccessDecision(
            allowed=False,
            state=AccessState.BUSINESS_REQUIRED,
            title="Подключите Telegram Business",
            message=next_action,
            next_step="connect_business",
            progress=progress,
        )
    if stage == "referral":
        return AccessDecision(
            allowed=False,
            state=AccessState.REFERRAL_REQUIRED,
            title="Пригласите друга или оплатите доступ",
            message=next_action,
            next_step="invite_or_pay",
            progress=progress,
        )
    if stage == "active":
        source = str(access.get("source") or "active")
        return AccessDecision(
            allowed=True,
            state=AccessState.TRIAL_ACTIVE if source == "trial" else AccessState.ACTIVE,
            title="Доступ активен",
            message=next_action,
            next_step=None,
            progress=progress,
            valid_until=access.get("ends_at") if isinstance(access.get("ends_at"), str) else None,
        )

    return AccessDecision(
        allowed=False,
        state=AccessState.PAYMENT_REQUIRED,
        title="Требуется оплата",
        message=next_action,
        next_step="pay",
        progress=progress,
    )
