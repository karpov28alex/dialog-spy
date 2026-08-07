from pathlib import Path


def test_dialog_list_exposes_full_history_metrics() -> None:
    schemas = Path("app/modules/archive/schemas.py").read_text(encoding="utf-8")
    repository = Path("app/modules/archive/repository.py").read_text(encoding="utf-8")
    service = Path("app/modules/archive/service.py").read_text(encoding="utf-8")
    assert "edited_count: int = 0" in schemas
    assert "deleted_count: int = 0" in schemas
    assert "media_count: int = 0" in schemas
    assert "dialog_metrics" in repository
    assert "last_messages" in repository
    assert 'edited_count=int(values.get("edited_count", 0))' in service


def test_miniapp_filters_use_backend_archive_metrics() -> None:
    index = Path("app/static/miniapp/index.html").read_text(encoding="utf-8")
    bridge = Path("app/static/miniapp/archive-metrics.js").read_text(encoding="utf-8")
    runtime = Path("app/static/miniapp/runtime-fixes.js").read_text(encoding="utf-8")
    assert "/app/archive-metrics.js?v=0.17.8" in index
    assert "/app/runtime-fixes.js?v=0.17.8" in index
    assert "item.edited_count" in bridge
    assert "item.deleted_count" in bridge
    assert "item.media_count" in bridge
    assert "archive-metric-markers" in bridge
    assert "archiveEdited" in runtime
    assert "archiveDeleted" in runtime
    assert "archiveMedia" in runtime


def test_statistics_share_uses_callback_photo_card() -> None:
    setup = Path("app/bot/setup.py").read_text(encoding="utf-8")
    share = Path("app/bot/statistics_share_card.py").read_text(encoding="utf-8")
    assert "product_experience_module._stats_keyboard = stats_keyboard" in setup
    assert "statistics_share_card_router" in setup
    assert 'callback_data="product:share_card"' in share
    assert "answer_photo" in share
    assert "Получить свою статистику" in share
    assert "start=ref_" in share
