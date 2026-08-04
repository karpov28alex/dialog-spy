from app.main import app
from app.modules.archive.router import router
from app.modules.archive.schemas import DialogListItem, DialogListResponse


def test_archive_v2_dialog_route_is_typed() -> None:
    route = next(route for route in router.routes if route.path == "/api/v2/archive/dialogs")
    assert route.response_model is DialogListResponse


def test_archive_v2_router_is_registered_in_application() -> None:
    paths = {path for route in app.routes if (path := getattr(route, "path", None))}
    assert "/api/v2/archive/dialogs" in paths


def test_archive_v2_router_does_not_depend_on_legacy_user_routes() -> None:
    source = __import__("pathlib").Path("app/modules/archive/router.py").read_text(encoding="utf-8")
    assert "app.api.routes.user" not in source
    assert "app.modules.archive.access" in source


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
