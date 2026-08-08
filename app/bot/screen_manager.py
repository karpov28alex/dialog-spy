from __future__ import annotations

from contextlib import suppress
from typing import Awaitable, Callable, TypeVar

from aiogram.types import CallbackQuery, Message
from redis.asyncio import Redis

from app.core.config import get_settings

settings = get_settings()
_SCREEN_KEY = "dialog_spy:screen:"
T = TypeVar("T")


def _redis() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)


async def clear_screen(chat_id: int, *, current_message_id: int | None = None, bot=None) -> None:
    """Delete the previously registered bot screen and the callback message when possible."""
    redis = _redis()
    try:
        previous = await redis.get(f"{_SCREEN_KEY}{chat_id}")
        ids = {int(previous)} if previous and previous.isdigit() else set()
        if current_message_id:
            ids.add(current_message_id)
        if bot:
            for message_id in ids:
                with suppress(Exception):
                    await bot.delete_message(chat_id, message_id)
        await redis.delete(f"{_SCREEN_KEY}{chat_id}")
    finally:
        await redis.aclose()


async def replace_callback(callback: CallbackQuery) -> None:
    if not callback.message:
        return
    await clear_screen(
        callback.message.chat.id,
        current_message_id=callback.message.message_id,
        bot=callback.bot,
    )


async def register_screen(message: Message) -> Message:
    redis = _redis()
    try:
        await redis.set(f"{_SCREEN_KEY}{message.chat.id}", str(message.message_id), ex=86400)
    finally:
        await redis.aclose()
    return message


async def send_screen(sender: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
    result = await sender(*args, **kwargs)
    if isinstance(result, Message):
        await register_screen(result)
    return result
