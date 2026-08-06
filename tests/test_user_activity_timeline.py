from pathlib import Path


def test_user_activity_model_and_migration_exist() -> None:
    model = Path("app/db/activity_models.py").read_text(encoding="utf-8")
    migration = Path("alembic/versions/0009_user_activity_logs.py").read_text(encoding="utf-8")
    assert "class UserActivityLog" in model
    assert "user_activity_logs" in model
    assert 'revision = "0009"' in migration
    assert 'down_revision = "0008"' in migration
    assert "ix_user_activity_logs_user_created" in migration


def test_activity_records_connection_permissions_and_dialog_changes() -> None:
    source = Path("app/services/user_activity.py").read_text(encoding="utf-8")
    for event_type in (
        "connection_enabled",
        "connection_disabled",
        "connection_rights_changed",
        "dialog_discovered",
        "dialog_hidden",
        "dialog_restored",
        "dialog_muted",
        "dialog_unmuted",
    ):
        assert event_type in source
    assert '@event.listens_for(BusinessConnection, "after_update")' in source
    assert '@event.listens_for(Dialog, "after_update")' in source


def test_web_admin_exposes_searchable_activity_page() -> None:
    source = Path("app/api/routes/admin_activity.py").read_text(encoding="utf-8")
    compat = Path("app/api/routes/webhook_compat.py").read_text(encoding="utf-8")
    assert "/api/admin/activity" in source
    assert "/api/admin/activity/users/{user_id}" in source
    assert "/admin/activity-log" in source
    assert "Telegram ID или событие" in source
    assert "router.include_router(activity_router)" in compat
