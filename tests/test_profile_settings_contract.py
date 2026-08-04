from pathlib import Path

from app.db.models import UserSettings


def test_user_settings_have_master_controls() -> None:
    assert UserSettings.notifications_enabled.default.arg is True
    assert UserSettings.save_protected_media.default.arg is True


def test_miniapp_profile_exposes_functional_controls() -> None:
    source = Path("app/static/miniapp/app.js").read_text(encoding="utf-8")
    assert "data-go=\"profile\"" in source
    assert "notifications_enabled" in source
    assert "save_protected_media" in source
    assert "await api('/api/me')" in source
    assert "await api('/api/settings')" in source


def test_webhook_delegates_master_notification_switches() -> None:
    webhook = Path("app/api/routes/webhook.py").read_text(encoding="utf-8")
    media_queue = Path("app/modules/media/queue.py").read_text(encoding="utf-8")
    assert "MediaQueueService" in webhook
    assert "EventContextService" in webhook
    assert "preferences.save_protected_media" in media_queue
    assert "preferences.notifications_enabled" in media_queue
    assert "protected_reply_is_allowed(" in media_queue
    assert 'kind="deliver_protected_media"' in media_queue
