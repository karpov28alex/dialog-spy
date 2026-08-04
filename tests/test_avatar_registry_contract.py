from pathlib import Path


def test_avatar_registry_migration_is_linear() -> None:
    source = Path("alembic/versions/0008_dialog_avatar_registry.py").read_text(encoding="utf-8")
    assert 'revision = "0008"' in source
    assert 'down_revision = "0007"' in source
    assert '"dialog_avatars"' in source
    assert '"ix_dialog_avatars_backfill"' in source


def test_avatar_endpoint_never_waits_for_telegram_download() -> None:
    source = Path("app/api/routes/avatar.py").read_text(encoding="utf-8")
    endpoint = source.split('@router.get("/avatar/{token}"', 1)[1]
    assert "await refresh_avatar(" not in endpoint
    assert "_schedule(" in endpoint
    assert 'headers["X-Avatar-Pending"] = "1"' in source
    assert '"Cache-Control": "no-store" if pending' in source


def test_registry_classifies_permanent_and_retryable_results() -> None:
    source = Path("app/services/dialog_avatars.py").read_text(encoding="utf-8")
    assert 'UNAVAILABLE = "unavailable"' in source
    assert 'NO_PHOTO = "no_photo"' in source
    assert 'RETRY = "retry"' in source
    assert '"user not found" in message' in source
    assert "timedelta(days=7)" in source
    assert "timedelta(minutes=15)" in source


def test_backfill_has_rate_control_and_summary() -> None:
    source = Path("scripts/backfill_dialog_avatars.py").read_text(encoding="utf-8")
    assert 'parser.add_argument("--delay"' in source
    assert 'parser.add_argument("--force"' in source
    assert 'print("\\nSummary:")' in source
