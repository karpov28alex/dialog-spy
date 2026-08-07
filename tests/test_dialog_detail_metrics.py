from pathlib import Path


def test_dialog_detail_exposes_full_history_metrics() -> None:
    schemas = Path("app/modules/archive/schemas.py").read_text(encoding="utf-8")
    service = Path("app/modules/archive/service.py").read_text(encoding="utf-8")
    assert "class DialogMetrics" in schemas
    assert "metrics: DialogMetrics" in schemas
    assert "dialog_metrics([dialog.id])" in service
    assert "message_count=int(values.get(\"message_count\", 0))" in service
    assert "edited_count=int(values.get(\"edited_count\", 0))" in service
    assert "deleted_count=int(values.get(\"deleted_count\", 0))" in service


def test_thread_filters_use_real_message_state() -> None:
    app = Path("app/static/miniapp/app.js").read_text(encoding="utf-8")
    suite = Path("app/static/miniapp/phantom-suite.js").read_text(encoding="utf-8")
    assert "data-msg-edited" in app
    assert "data-msg-deleted" in app
    assert "data-msg-media" in app
    assert "message.dataset.msgEdited === '1'" in suite
    assert "message.dataset.msgDeleted === '1'" in suite
    assert "message.dataset.msgMedia === '1'" in suite
    assert "d.metrics" in suite
