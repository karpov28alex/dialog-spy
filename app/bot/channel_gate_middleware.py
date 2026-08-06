from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, TelegramObject

from app.bot.handlers import is_admin
from app.services.access_funnel import channel_gate_passed, get_funnel_config


ADMIN_COMMANDS = {
    "/admin",
    "/admin_id",
    "/admins",
    "/broadcast",
}
ADMIN_CALLBACK_PREFIXES = (
    "crm:",
    "admin:",
    "funnel:admin",
    "funnel:toggle:",
    "funnel:fields:",
    "funnel:edit:",
)
# Informational and account controls stay available before the channel gate.
# The gate controls access/trial activation, not navigation through the bot.
USER_COMMANDS = {
    "/start",
    "/menu",
    "/profile",
    "/settings",
    "/stats",
    "/help",
    "/app",
    "/access",
    "/subscription",
    "/cancel",
}
USER_CALLBACK_PREFIXES = (
    "user:",
    "product:",
    "help",
    "funnel:check_channel",
)
GROUP_TYPES = {"group", "supergroup"}


def _subscription_keyboard(channel_url: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if channel_url.startswith("https://"):
        rows.append([InlineKeyboardButton(text="📢 Подписаться на канал", url=channel_url)])
    rows.append([InlineKeyboardButton(text="✅ Проверить подписку", callback_data="funnel:check_channel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _message_command(event: Message) -> str:
    text = (event.text or "").strip()
    if not text.startswith("/"):
        return ""
    return text.split(maxsplit=1)[0].split("@", 1)[0].lower()


def _is_admin_control(event: TelegramObject) -> bool:
    if isinstance(event, Message):
        return _message_command(event) in ADMIN_COMMANDS
    if isinstance(event, CallbackQuery):
        callback_data = event.data or ""
        return callback_data.startswith(ADMIN_CALLBACK_PREFIXES)
    return False


def _is_user_navigation(event: TelegramObject) -> bool:
    if isinstance(event, Message):
        return _message_command(event) in USER_COMMANDS
    if isinstance(event, CallbackQuery):
        callback_data = event.data or ""
        return callback_data.startswith(USER_CALLBACK_PREFIXES)
    return False


class ChannelGateMiddleware(BaseMiddleware):
    """Protect gated product actions without hiding the public user menu."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and str(event.chat.type) in GROUP_TYPES:
            return await handler(event, data)

        user = data.get("event_from_user")
        user_id = getattr(user, "id", None)
        if user_id is None:
            return await handler(event, data)

        # Profile, statistics, settings, subscription and help explain the
        # current connection state themselves and must always remain usable.
        if _is_user_navigation(event):
            return await handler(event, data)

        if _is_admin_control(event) and await is_admin(user_id):
            return await handler(event, data)

        config = await get_funnel_config()
        if not config.enabled or not config.channel_required:
            return await handler(event, data)

        bot = data.get("bot")
        if bot is not None and await channel_gate_passed(bot, user_id=user_id, config=config):
            return await handler(event, data)

        markup = _subscription_keyboard(config.channel_url)
        if isinstance(event, CallbackQuery):
            await event.answer("Сначала подпишитесь на информационный канал.", show_alert=True)
            if event.message:
                await event.message.answer(config.subscription_text, reply_markup=markup)
        elif isinstance(event, Message):
            await event.answer(config.subscription_text, reply_markup=markup)
        return None
