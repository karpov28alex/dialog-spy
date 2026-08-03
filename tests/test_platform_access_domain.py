from app.platform.access.domain import AccessState, decision_from_access_center


def test_channel_is_required_first() -> None:
    decision = decision_from_access_center(
        {"stage": "channel", "progress": 0, "next_action": "Подпишитесь."}
    )
    assert decision.allowed is False
    assert decision.state is AccessState.CHANNEL_REQUIRED
    assert decision.next_step == "verify_channel"


def test_business_starts_before_trial() -> None:
    decision = decision_from_access_center(
        {"stage": "business", "progress": 25, "next_action": "Подключите Business."}
    )
    assert decision.allowed is False
    assert decision.state is AccessState.BUSINESS_REQUIRED
    assert decision.progress == 25


def test_trial_is_allowed() -> None:
    decision = decision_from_access_center(
        {
            "stage": "active",
            "progress": 75,
            "next_action": "Пробный период активен.",
            "access": {"source": "trial", "ends_at": "2026-08-06T10:00:00+00:00"},
        }
    )
    assert decision.allowed is True
    assert decision.state is AccessState.TRIAL_ACTIVE
    assert decision.valid_until == "2026-08-06T10:00:00+00:00"


def test_paid_access_is_allowed() -> None:
    decision = decision_from_access_center(
        {
            "stage": "active",
            "progress": 100,
            "next_action": "Доступ активен.",
            "access": {"source": "vip", "ends_at": None},
        }
    )
    assert decision.allowed is True
    assert decision.state is AccessState.ACTIVE


def test_unknown_stage_requires_payment() -> None:
    decision = decision_from_access_center(
        {"stage": "unexpected", "progress": 999, "next_action": "Оплатите."}
    )
    assert decision.allowed is False
    assert decision.state is AccessState.PAYMENT_REQUIRED
    assert decision.progress == 100
