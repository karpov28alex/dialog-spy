from pathlib import Path


def test_v019_instruction_uses_published_media_sender() -> None:
    source = Path("app/bot/navigation_v019.py").read_text(encoding="utf-8")
    block = source[source.index("async def help_screen"):]
    assert "from app.bot.instruction_publisher import send_public_instruction" in block
    assert "await send_public_instruction(callback.message)" in block
    assert "instruction_content" not in block
    assert 'content["text"]' not in block


def test_public_instruction_sender_renders_published_media() -> None:
    source = Path("app/bot/instruction_publisher.py").read_text(encoding="utf-8")
    assert "await _send_payload(message, await published_instruction())" in source
    assert "InputMediaPhoto" in source
    assert "InputMediaVideo" in source
    assert "answer_media_group" in source
