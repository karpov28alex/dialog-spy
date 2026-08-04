from app.bot.setup import dispatcher


def _callback_name(handler) -> str:
    return getattr(handler.callback, "__name__", "")


def test_dispatcher_has_one_active_start_handler() -> None:
    names = [
        _callback_name(handler)
        for router in dispatcher.sub_routers
        for handler in router.message.handlers
        if _callback_name(handler) == "start"
    ]
    assert names == ["start"]
