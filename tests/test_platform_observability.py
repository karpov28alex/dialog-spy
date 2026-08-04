from pathlib import Path

from app.main import app
from app.observability.metrics import RuntimeMetrics


def test_metrics_are_rendered_in_prometheus_format() -> None:
    metrics = RuntimeMetrics()
    metrics.observe_http(
        method="GET",
        route="/api/dialogs/{dialog_id}",
        status_code=200,
        duration_seconds=0.125,
    )

    output = metrics.render_prometheus()

    assert "dialog_spy_http_requests_total" in output
    assert 'route="/api/dialogs/{dialog_id}"' in output
    assert "dialog_spy_http_request_duration_seconds_sum" in output
    assert " 0.125000000" in output


def test_metrics_and_health_routes_are_registered() -> None:
    source = Path("app/main.py").read_text(encoding="utf-8")
    assert "app.include_router(observability_router)" in source
    assert 'app.add_middleware(MetricsMiddleware)' in source
    assert '"latency_ms": database_ms' in source
    assert '"latency_ms": redis_ms' in source


def test_operational_index_migration_targets_hot_paths() -> None:
    source = Path("alembic/versions/0007_operational_indexes.py").read_text(
        encoding="utf-8"
    )
    assert "ix_jobs_queue_ready" in source
    assert "WHERE status = 'queued'" in source
    assert "ix_jobs_running_locked" in source
    assert "ix_dialogs_owner_last_message" in source
    assert "ix_messages_dialog_sent" in source
    assert "ix_message_versions_message_version" in source
    assert "ix_media_message_id" in source


def test_metrics_route_is_hidden_from_openapi() -> None:
    source = Path("app/observability/router.py").read_text(encoding="utf-8")
    assert 'router.get("/metrics", include_in_schema=False' in source


def test_application_object_remains_importable() -> None:
    assert app.title == "Dialog Spy API"
