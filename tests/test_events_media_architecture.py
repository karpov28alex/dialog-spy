from pathlib import Path


def test_webhook_is_an_orchestrator() -> None:
    source = Path("app/api/routes/webhook.py").read_text(encoding="utf-8")
    assert "EventContextService" in source
    assert "MediaQueueService" in source
    assert "select(Media)" not in source
    assert "select(BusinessConnection)" not in source
    assert "protected_reply_is_allowed" not in source


def test_event_context_has_no_http_dependency() -> None:
    source = Path("app/modules/events/context.py").read_text(encoding="utf-8")
    assert "fastapi" not in source
    assert "redis" not in source


def test_media_queue_owns_media_jobs() -> None:
    source = Path("app/modules/media/queue.py").read_text(encoding="utf-8")
    assert 'kind="download_media"' in source
    assert 'kind="deliver_protected_media"' in source
    assert "save_business_message" in source
