from pathlib import Path


def test_instruction_editor_requires_explicit_publish() -> None:
    source = Path("app/bot/instruction_publisher.py").read_text(encoding="utf-8")

    assert "Сохранить и опубликовать" in source
    assert "Отменить изменения" in source
    assert 'callback_data="crm:instruction_publish"' in source
    assert 'callback_data="crm:instruction_discard"' in source
    assert "PUBLISHED_KEY" in source
    assert "DRAFT_PREFIX" in source
    assert "await _publish(callback.from_user.id)" in source


def test_preview_uses_draft_and_public_help_uses_published_version() -> None:
    source = Path("app/bot/instruction_publisher.py").read_text(encoding="utf-8")

    assert "await _send_payload(callback.message, value, preview=True)" in source
    assert "await _send_payload(message, await published_instruction())" in source
    assert "Изменения сохраняются в черновик" in source
    assert "Пользователи увидят их только после публикации" in source


def test_instruction_publisher_is_mounted_before_generic_handlers() -> None:
    setup = Path("app/bot/setup.py").read_text(encoding="utf-8")

    include = "dispatcher.include_router(instruction_publisher_router)"
    assert include in setup
    assert setup.index(include) < setup.index("dispatcher.include_router(access_funnel_router)")
