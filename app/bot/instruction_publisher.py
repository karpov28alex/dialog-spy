from __future__ import annotations

import json
from typing import Any

from aiogram import F, Router
from aiogram.filters import BaseFilter, Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputMediaVideo,
    Message,
)
from redis.asyncio import Redis

from app.bot.admin_console import is_admin
from app.bot.handlers import DEFAULT_INSTRUCTION, INSTRUCTION_KEY
from app.core.config import get_settings

router = Router(name="instruction-publisher")
settings = get_settings()

PUBLISHED_KEY = "dialog_spy:bot_instruction_v3"
V2_KEY = "dialog_spy:bot_instruction_v2"
DRAFT_PREFIX = "dialog_spy:instruction_draft:"
LEGACY_MENU_KEY = "dialog_spy:user_menu_content"


def _redis() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)


def _keyboard(rows: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=rows)


def editor_keyboard() -> InlineKeyboardMarkup:
    return _keyboard([
        [InlineKeyboardButton(text="👁 Предпросмотр", callback_data="crm:instruction_preview")],
        [InlineKeyboardButton(text="✏️ Изменить текст", callback_data="crm:instruction_text")],
        [InlineKeyboardButton(text="➕ Добавить медиа", callback_data="crm:instruction_media")],
        [InlineKeyboardButton(text="🗑 Очистить медиа в черновике", callback_data="crm:instruction_clear")],
        [InlineKeyboardButton(text="💾 Сохранить и опубликовать", callback_data="crm:instruction_publish")],
        [InlineKeyboardButton(text="↩️ Отменить изменения", callback_data="crm:instruction_discard")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="crm:home")],
    ])


def preview_keyboard() -> InlineKeyboardMarkup:
    return _keyboard([
        [InlineKeyboardButton(text="💾 Сохранить и опубликовать", callback_data="crm:instruction_publish")],
        [InlineKeyboardButton(text="✏️ Продолжить редактирование", callback_data="crm:instruction")],
        [InlineKeyboardButton(text="↩️ Отменить изменения", callback_data="crm:instruction_discard")],
    ])


async def _legacy_payload(redis: Redis) -> dict[str, Any]:
    raw_v2 = await redis.get(V2_KEY)
    if raw_v2:
        try:
            value = json.loads(raw_v2)
            return {
                "text": value.get("text") or DEFAULT_INSTRUCTION,
                "media": list(value.get("media") or [])[:10],
            }
        except (TypeError, ValueError, json.JSONDecodeError):
            pass

    legacy = await redis.hgetall(INSTRUCTION_KEY)
    menu_text = await redis.hget(LEGACY_MENU_KEY, "instruction")
    media = []
    for key in ("video1", "video2"):
        if legacy.get(key):
            media.append({"type": "video", "file_id": legacy[key]})
    return {
        "text": menu_text or legacy.get("text") or DEFAULT_INSTRUCTION,
        "media": media,
    }


async def published_instruction() -> dict[str, Any]:
    redis = _redis()
    try:
        raw = await redis.get(PUBLISHED_KEY)
        if raw:
            try:
                value = json.loads(raw)
                return {
                    "text": value.get("text") or DEFAULT_INSTRUCTION,
                    "media": list(value.get("media") or [])[:10],
                }
            except (TypeError, ValueError, json.JSONDecodeError):
                pass
        value = await _legacy_payload(redis)
        await redis.set(PUBLISHED_KEY, json.dumps(value, ensure_ascii=False))
        return value
    finally:
        await redis.aclose()


async def _draft(user_id: int, *, create: bool = True) -> dict[str, Any] | None:
    redis = _redis()
    try:
        raw = await redis.get(f"{DRAFT_PREFIX}{user_id}")
        if raw:
            return json.loads(raw)
        if not create:
            return None
        value = await published_instruction()
        await redis.set(
            f"{DRAFT_PREFIX}{user_id}",
            json.dumps(value, ensure_ascii=False),
            ex=86400,
        )
        return value
    finally:
        await redis.aclose()


async def _save_draft(user_id: int, value: dict[str, Any]) -> None:
    redis = _redis()
    try:
        await redis.set(
            f"{DRAFT_PREFIX}{user_id}",
            json.dumps(value, ensure_ascii=False),
            ex=86400,
        )
    finally:
        await redis.aclose()


async def _discard(user_id: int) -> None:
    redis = _redis()
    try:
        await redis.delete(f"{DRAFT_PREFIX}{user_id}")
    finally:
        await redis.aclose()


async def _publish(user_id: int) -> dict[str, Any]:
    value = await _draft(user_id)
    assert value is not None
    redis = _redis()
    try:
        await redis.set(PUBLISHED_KEY, json.dumps(value, ensure_ascii=False))
        await redis.set(V2_KEY, json.dumps(value, ensure_ascii=False))
        mapping = {"text": value.get("text") or DEFAULT_INSTRUCTION}
        videos = [x["file_id"] for x in value.get("media", []) if x.get("type") == "video"]
        mapping["video1"] = videos[0] if videos else ""
        mapping["video2"] = videos[1] if len(videos) > 1 else ""
        await redis.hset(INSTRUCTION_KEY, mapping=mapping)
        await redis.hdel(LEGACY_MENU_KEY, "instruction")
        await redis.delete(f"{DRAFT_PREFIX}{user_id}")
    finally:
        await redis.aclose()
    return value


async def _send_payload(message: Message, value: dict[str, Any], *, preview: bool = False) -> None:
    media = list(value.get("media") or [])[:10]
    album = [
        InputMediaPhoto(media=item["file_id"])
        if item.get("type") == "photo"
        else InputMediaVideo(media=item["file_id"])
        for item in media
        if item.get("file_id") and item.get("type") in {"photo", "video"}
    ]
    if len(album) > 1:
        await message.answer_media_group(album)
    elif len(album) == 1:
        item = media[0]
        if item.get("type") == "photo":
            await message.answer_photo(item["file_id"])
        else:
            await message.answer_video(item["file_id"], supports_streaming=True)

    markup = preview_keyboard() if preview else _keyboard([
        [InlineKeyboardButton(text="👤 В профиль", callback_data="user:profile")]
    ])
    prefix = "<b>👁 Предпросмотр черновика</b>\n\n" if preview else ""
    await message.answer(prefix + (value.get("text") or DEFAULT_INSTRUCTION), reply_markup=markup)


async def send_public_instruction(message: Message) -> None:
    await _send_payload(message, await published_instruction())


class InstructionInput(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        if not message.from_user or not await is_admin(message.from_user.id):
            return False
        redis = _redis()
        try:
            mode = await redis.get(f"{DRAFT_PREFIX}{message.from_user.id}:mode")
            return mode in {"text", "media"}
        finally:
            await redis.aclose()


async def _set_mode(user_id: int, mode: str | None) -> None:
    redis = _redis()
    try:
        key = f"{DRAFT_PREFIX}{user_id}:mode"
        if mode:
            await redis.set(key, mode, ex=3600)
        else:
            await redis.delete(key)
    finally:
        await redis.aclose()


@router.message(Command("help"))
async def public_help_command(message: Message) -> None:
    await send_public_instruction(message)


@router.callback_query(F.data == "help")
async def public_help_callback(callback: CallbackQuery) -> None:
    if callback.message:
        await send_public_instruction(callback.message)
    await callback.answer()


@router.callback_query(F.data == "crm:instruction")
async def edit_instruction(callback: CallbackQuery) -> None:
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await _draft(callback.from_user.id)
    await _set_mode(callback.from_user.id, None)
    if callback.message:
        await callback.message.answer(
            "<b>📖 Редактор инструкции</b>\n\n"
            "Изменения сохраняются в черновик. Пользователи увидят их только после публикации.",
            reply_markup=editor_keyboard(),
        )
    await callback.answer()


@router.callback_query(F.data == "crm:instruction_text")
async def edit_text(callback: CallbackQuery) -> None:
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await _draft(callback.from_user.id)
    await _set_mode(callback.from_user.id, "text")
    if callback.message:
        await callback.message.answer("Отправьте новый текст инструкции.")
    await callback.answer()


@router.callback_query(F.data == "crm:instruction_media")
async def edit_media(callback: CallbackQuery) -> None:
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await _draft(callback.from_user.id)
    await _set_mode(callback.from_user.id, "media")
    if callback.message:
        await callback.message.answer(
            "Отправьте до 10 фото или видео. После добавления нажмите «Готово».",
            reply_markup=_keyboard([
                [InlineKeyboardButton(text="✅ Готово", callback_data="crm:instruction_media_done")],
                [InlineKeyboardButton(text="↩️ Отменить изменения", callback_data="crm:instruction_discard")],
            ]),
        )
    await callback.answer()


@router.callback_query(F.data == "crm:instruction_media_done")
async def media_done(callback: CallbackQuery) -> None:
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await _set_mode(callback.from_user.id, None)
    if callback.message:
        await callback.message.answer(
            "✅ Медиа добавлены в черновик. Нажмите «Предпросмотр», затем «Сохранить и опубликовать».",
            reply_markup=editor_keyboard(),
        )
    await callback.answer()


@router.callback_query(F.data == "crm:instruction_preview")
async def preview(callback: CallbackQuery) -> None:
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    value = await _draft(callback.from_user.id)
    if callback.message and value:
        await _send_payload(callback.message, value, preview=True)
    await callback.answer()


@router.callback_query(F.data == "crm:instruction_clear")
async def clear_media(callback: CallbackQuery) -> None:
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    value = await _draft(callback.from_user.id)
    assert value is not None
    value["media"] = []
    await _save_draft(callback.from_user.id, value)
    if callback.message:
        await callback.message.answer("🗑 Медиа удалены из черновика.", reply_markup=editor_keyboard())
    await callback.answer()


@router.callback_query(F.data == "crm:instruction_publish")
async def publish(callback: CallbackQuery) -> None:
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await _publish(callback.from_user.id)
    await _set_mode(callback.from_user.id, None)
    if callback.message:
        await callback.message.answer(
            "✅ Инструкция сохранена и опубликована. Пользователи уже получают новую версию.",
            reply_markup=editor_keyboard(),
        )
    await callback.answer("Опубликовано")


@router.callback_query(F.data == "crm:instruction_discard")
async def discard(callback: CallbackQuery) -> None:
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await _discard(callback.from_user.id)
    await _set_mode(callback.from_user.id, None)
    if callback.message:
        await callback.message.answer("↩️ Черновик удалён. Опубликованная инструкция не изменилась.")
    await callback.answer("Изменения отменены")


@router.message(InstructionInput())
async def instruction_input(message: Message) -> None:
    assert message.from_user is not None
    user_id = message.from_user.id
    redis = _redis()
    try:
        mode = await redis.get(f"{DRAFT_PREFIX}{user_id}:mode")
    finally:
        await redis.aclose()

    value = await _draft(user_id)
    assert value is not None
    if mode == "text":
        text = (message.text or message.caption or "").strip()
        if not text:
            await message.answer("Текст не может быть пустым.")
            return
        value["text"] = text
        await _save_draft(user_id, value)
        await _set_mode(user_id, None)
        await message.answer(
            "✅ Текст добавлен в черновик. Нажмите «Предпросмотр», затем «Сохранить и опубликовать».",
            reply_markup=editor_keyboard(),
        )
        return

    media = list(value.get("media") or [])
    if len(media) >= 10:
        await message.answer("Лимит — 10 файлов. Нажмите «Готово».")
        return
    if message.photo:
        media.append({"type": "photo", "file_id": message.photo[-1].file_id})
    elif message.video:
        media.append({"type": "video", "file_id": message.video.file_id})
    else:
        await message.answer("Поддерживаются фото и видео.")
        return
    value["media"] = media
    await _save_draft(user_id, value)
    await message.answer(
        f"Добавлено {len(media)}/10.",
        reply_markup=_keyboard([
            [InlineKeyboardButton(text="✅ Готово", callback_data="crm:instruction_media_done")],
            [InlineKeyboardButton(text="↩️ Отменить изменения", callback_data="crm:instruction_discard")],
        ]),
    )
