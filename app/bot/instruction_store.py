from __future__ import annotations

from redis.asyncio import Redis

from app.bot.handlers import DEFAULT_INSTRUCTION, INSTRUCTION_KEY
from app.core.config import get_settings

settings = get_settings()
LEGACY_MENU_KEY = "dialog_spy:user_menu_content"


async def instruction_content() -> dict[str, str]:
    """Read the instruction from the canonical store and migrate legacy edits.

    Older versions of the menu editor wrote the instruction text into
    ``dialog_spy:user_menu_content`` while the public help handler read
    ``dialog_spy:bot_instruction``. Prefer the legacy edit once, migrate it to
    the canonical hash and remove the stale field so future edits have a single
    source of truth.
    """
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        canonical = await redis.hgetall(INSTRUCTION_KEY)
        legacy_text = await redis.hget(LEGACY_MENU_KEY, "instruction")
        if legacy_text:
            await redis.hset(INSTRUCTION_KEY, "text", legacy_text)
            await redis.hdel(LEGACY_MENU_KEY, "instruction")
            canonical["text"] = legacy_text
        return {
            "text": canonical.get("text") or DEFAULT_INSTRUCTION,
            "video1": canonical.get("video1") or "",
            "video2": canonical.get("video2") or "",
        }
    finally:
        await redis.aclose()
