from pathlib import Path


def test_instruction_store_migrates_legacy_editor_value() -> None:
    source = Path("app/bot/instruction_store.py").read_text(encoding="utf-8")

    assert 'LEGACY_MENU_KEY = "dialog_spy:user_menu_content"' in source
    assert 'redis.hget(LEGACY_MENU_KEY, "instruction")' in source
    assert 'redis.hset(INSTRUCTION_KEY, "text", legacy_text)' in source
    assert 'redis.hdel(LEGACY_MENU_KEY, "instruction")' in source


def test_setup_uses_synchronized_instruction_reader_everywhere() -> None:
    source = Path("app/bot/setup.py").read_text(encoding="utf-8")

    assert "synchronized_instruction_content" in source
    assert "legacy_handlers.instruction_content = synchronized_instruction_content" in source
    assert "user_experience_module.instruction_content = synchronized_instruction_content" in source
