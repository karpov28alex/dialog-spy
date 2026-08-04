from pathlib import Path

from app.modules.archive.router import router
from app.modules.archive.schemas import (
    DialogDetailResponse,
    DialogListItem,
    DialogListResponse,
    MessageVersionsResponse,
    OperationResponse,
)


def route(path: str, method: str):
    return next(
        item
        for item in router.routes
        if item.path == path and method in getattr(item, "methods", set())
    )


def test_archive_v2_routes_are_typed() -> None:
    assert route("/api/v2/archive/dialogs", "GET").response_model is DialogListResponse
    assert (
        route("/api/v2/archive/dialogs/{dialog_id}", "GET").response_model
        is DialogDetailResponse
    )
    assert (
        route("/api/v2/archive/dialogs/{dialog_id}", "PATCH").response_model
        is OperationResponse
    )
    assert (
        route("/api/v2/archive/messages/{message_id}/versions", "GET").response_model
        is MessageVersionsResponse
    )


def test_archive_v2_router_is_registered_in_application() -> None:
    source = Path("app/main.py").read_text(encoding="utf-8")
    assert "from app.modules.archive import router as archive_v2_router" in source
    assert "app.include_router(archive_v2_router)" in source


def test_archive_v2_router_does_not_depend_on_legacy_user_routes() -> None:
    source = Path("app/modules/archive/router.py").read_text(encoding="utf-8")
    assert "app.api.routes.user" not in source
    assert "app.modules.archive.access" in source


def test_archive_detail_uses_batch_repository_queries() -> None:
    source = Path("app/modules/archive/service.py").read_text(encoding="utf-8")
    assert "media_for_messages(message_ids)" in source
    assert "versions_for_messages(message_ids)" in source


def test_dialog_list_response_preserves_public_shape() -> None:
    response = DialogListResponse(
        items=[
            DialogListItem(
                id=1,
                peer_name="Test",
                peer_username="test",
                avatar=None,
                message_count=2,
                last_message_at=None,
                last_message_text="hello",
                last_message_deleted=False,
                last_message_edited=False,
                direction="incoming",
                is_hidden=False,
            )
        ],
        next_cursor=None,
    )
    assert response.model_dump()["items"][0]["last_message_text"] == "hello"
