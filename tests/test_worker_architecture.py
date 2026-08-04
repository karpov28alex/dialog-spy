from pathlib import Path


def test_worker_runner_delegates_job_delivery() -> None:
    source = Path("app/worker/runner.py").read_text(encoding="utf-8")
    assert "WorkerHandlers" in source
    assert "handlers.handle(job)" in source
    assert "send_photo(" not in source
    assert "download_telegram_file(" not in source
    assert "is_protected_message(" not in source


def test_worker_handlers_own_supported_job_kinds() -> None:
    source = Path("app/worker/handlers.py").read_text(encoding="utf-8")
    for kind in (
        '"send_text"',
        '"broadcast_send"',
        '"download_media"',
        '"send_protected_media"',
        '"deliver_protected_media"',
    ):
        assert kind in source
    assert "Unknown job kind" in source


def test_worker_runner_owns_queue_lifecycle() -> None:
    source = Path("app/worker/runner.py").read_text(encoding="utf-8")
    assert "recover_stale_running_jobs" in source
    assert "recover_queued_jobs" in source
    assert "reschedule" in source
    assert "mark_forbidden" in source
    assert "QUEUE_MARKER_PREFIX" in source
