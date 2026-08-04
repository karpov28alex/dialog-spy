from pathlib import Path


def test_start_has_one_canonical_owner() -> None:
    setup = Path("app/bot/setup.py").read_text(encoding="utf-8")
    assert '_drop_named_handlers(legacy_command_router.message, {"start"})' in setup
    assert "dispatcher.include_router(access_funnel_router)" in setup
    assert "dispatcher.include_router(user_handlers.router)" not in setup


def test_legacy_callback_routers_are_not_dispatched_twice() -> None:
    setup = Path("app/bot/setup.py").read_text(encoding="utf-8")
    assert "legacy_command_router.callback_query.handlers.clear()" in setup
    assert "legacy_admin_router.callback_query.handlers.clear()" in setup


def test_webhook_keeps_database_update_deduplication() -> None:
    webhook = Path("app/api/routes/webhook.py").read_text(encoding="utf-8")
    assert "claim_update(session, update_id, kind)" in webhook
    assert "telegram_update_duplicate" in webhook
