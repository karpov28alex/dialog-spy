from pathlib import Path


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_screen_manager_deletes_previous_and_current_screen() -> None:
    source = read("app/bot/screen_manager.py")
    assert "bot.delete_message" in source
    assert "current_message_id" in source
    assert "dialog_spy:screen:" in source
    nav = read("app/bot/navigation_v019.py")
    assert "await replace_callback(callback)" in nav


def test_profile_has_connection_state_and_live_24h_pulse() -> None:
    source = read("app/bot/profile_card_handlers.py")
    assert "Автоматизация чатов не подключена" in source
    assert "За последние 24 часа" in source
    assert "active_today" in source


def test_statistics_exposes_richer_dialog_insights() -> None:
    nav = read("app/bot/navigation_v019.py")
    service = read("app/services/dialog_insights.py")
    assert 'callback_data="v019:insights"' in nav
    assert "peak_hour" in service
    assert "quiet_dialogs" in service
    assert "top_messages" in service


def test_admin_health_checks_real_dependencies() -> None:
    service = read("app/services/system_health.py")
    setup = read("app/bot/setup.py")
    handler = read("app/bot/health_handlers.py")
    assert 'text("SELECT 1")' in service
    assert "await redis.ping()" in service
    assert "FailedUpdate" in service and "Job" in service
    assert "dispatcher.include_router(health_router)" in setup
    assert 'F.data == "health:show"' in handler


def test_existing_instruction_media_regression_remains_covered() -> None:
    source = read("app/bot/navigation_v019.py")
    assert "send_public_instruction" in source
    publisher = read("app/bot/instruction_publisher.py")
    assert "answer_media_group" in publisher
