from pathlib import Path


def test_finance_center_exposes_real_charge_and_bonus_actions() -> None:
    source = Path("app/static/admin/billing-mobile.html").read_text(encoding="utf-8")
    assert "Финансовый центр" in source
    assert "Ручное списание" in source
    assert "/api/admin/impaya/manual-charge/prepare" in source
    assert "/confirm" in source
    assert "Бонусный VIP" in source
    assert "/api/admin/user360/users/" in source
    assert "kind:'vip'" in source


def test_finance_center_does_not_fake_provider_refunds() -> None:
    source = Path("app/static/admin/billing-mobile.html").read_text(encoding="utf-8")
    assert "Автоматический возврат через Impaya пока не подключён" in source
    assert "не будет показывать ложный успешный возврат" in source
    assert "ID платежа" in source


def test_finance_center_is_mobile_first_and_links_to_user360() -> None:
    source = Path("app/static/admin/billing-mobile.html").read_text(encoding="utf-8")
    assert "viewport-fit=cover" in source
    assert "@media(max-width:430px)" in source
    assert "/admin/user360-mobile.html?user_id=" in source
    assert "cache:'no-store'" in source
