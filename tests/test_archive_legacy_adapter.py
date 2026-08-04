from pathlib import Path

from app.api.routes.user import router as user_router
from app.modules.archive.legacy_router import router as legacy_router


def test_legacy_archive_paths_remain_available() -> None:
    paths = {route.path for route in legacy_router.routes}
    assert "/dialogs" in paths
    assert "/dialogs/{dialog_id}" in paths
    assert "/messages/{message_id}/versions" in paths
    assert "/media/download/{token}" in paths


def test_user_router_mounts_archive_adapter() -> None:
    paths = {route.path for route in user_router.routes}
    assert "/api/dialogs" in paths
    assert "/api/dialogs/{dialog_id}" in paths


def test_user_module_no_longer_owns_archive_sql() -> None:
    source = Path("app/api/routes/user.py").read_text(encoding="utf-8")
    assert "ArchiveRepository" not in source
    assert "MessageVersion" not in source
    assert "safe_media_path" not in source
    assert "legacy_archive_router" in source


def test_legacy_adapter_delegates_to_archive_service() -> None:
    source = Path("app/modules/archive/legacy_router.py").read_text(encoding="utf-8")
    assert "ArchiveService" in source
    assert "ArchiveRepository" in source
    assert "select(" not in source
