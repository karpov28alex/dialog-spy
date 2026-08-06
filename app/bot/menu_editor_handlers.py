from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from redis.asyncio import Redis

from app.bot.handlers import INSTRUCTION_KEY, is_admin
from app.core.config import get_settings

router = Router(name="menu-editor")
settings = get_settings()
CONTENT_KEY = "dialog_spy:user_menu_content"
BUTTONS = {
    "show_miniapp": "Mini App",
    "show_stats": "Статистика",
    "show_subscription": "Подписка",
    "show_profile": "Профиль",
    "show_settings": "Настройки",
    "show_instruction": "Инструкция",
    "show_offer": "Оферта",
}
DEFAULTS = {
    "settings": "Зелёная отметка означает, что функция включена. Нажмите кнопку для переключения.",
    "offer_url": "https://mooncloud.ltd/spy/terms.html#free",
    **{field: "1" for field in BUTTONS},
}


class MenuEdit(StatesGroup):
    settings = State()
    offer = State()
    instruction = State()


async def get_menu_content() -> dict[str, str]:
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        data = await redis.hgetall(CONTENT_KEY)
    finally:
        await redis.aclose()
    return {**DEFAULTS, **{key: value for key, value in data.items() if value}}


async def set_menu_content(field: str, value: str) -> None:
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        if field == "instruction":
            await redis.hset(INSTRUCTION_KEY, "text", value)
        else:
            await redis.hset(CONTENT_KEY, field, value)
    finally:
        await redis.aclose()


def _is_enabled(data: dict[str, str], field: str) -> bool:
    return data.get(field, "1") not in {"0", "false", "False", "off"}


def editor_keyboard(data: dict[str, str] | None = None) -> InlineKeyboardMarkup:
    data = data or DEFAULTS
    rows = [
        [InlineKeyboardButton(text="⚙️ Текст настроек", callback_data="menuedit:settings")],
        [InlineKeyboardButton(text="📄 Ссылка оферты", callback_data="menuedit:offer")],
        [InlineKeyboardButton(text="📖 Текст инструкции", callback_data="menuedit:instruction")],
    ]
    for field, label in BUTTONS.items():
        rows.append([
            InlineKeyboardButton(
                text=f"{'✅' if _is_enabled(data, field) else '❌'} Кнопка «{label}»",
                callback_data=f"menuedit:toggle:{field}",
            )
        ])
    rows.extend([
        [InlineKeyboardButton(text="👁 Предпросмотр", callback_data="menuedit:preview")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="menuedit:cancel")],
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _editor_markup() -> InlineKeyboardMarkup:
    return editor_keyboard(await get_menu_content())


def _subscription_keyboard(admin: bool) -> InlineKeyboardMarkup:
    from app.bot.enhanced_user_menu import enhanced_user_keyboard

    base = enhanced_user_keyboard(admin=admin)
    rows = [[InlineKeyboardButton(text="🚫 Отключить автопродление", callback_data="user:subscription:cancel")]]
    rows.extend([list(row) for row in base.inline_keyboard])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(Command("settings"))
async def configurable_settings_command(message: Message) -> None:
    from app.bot import user_handlers

    if not message.from_user:
        return
    prefs = await user_handlers._settings(message.from_user.id)
    if prefs is None:
        await message.answer("Профиль ещё не создан. Отправьте /start.")
        return
    content = await get_menu_content()
    await message.answer(
        f"<b>⚙️ Настройки</b>\n\n{content['settings']}",
        reply_markup=user_handlers.settings_keyboard(prefs),
    )


@router.callback_query(F.data == "user:settings")
async def configurable_settings_callback(callback: CallbackQuery) -> None:
    from app.bot import user_handlers

    prefs = await user_handlers._settings(callback.from_user.id)
    if callback.message and prefs:
        content = await get_menu_content()
        await callback.message.answer(
            f"<b>⚙️ Настройки</b>\n\n{content['settings']}",
            reply_markup=user_handlers.settings_keyboard(prefs),
        )
    await callback.answer()


@router.callback_query(F.data == "user:subscription")
async def subscription_callback(callback: CallbackQuery) -> None:
    from app.bot import user_handlers

    if callback.message:
        text = await user_handlers._subscription_text(callback.from_user.id)
        await callback.message.answer(
            text,
            reply_markup=_subscription_keyboard(await is_admin(callback.from_user.id)),
        )
    await callback.answer()


@router.callback_query(F.data == "user:subscription:cancel")
async def subscription_cancel_callback(callback: CallbackQuery) -> None:
    from app.bot import user_handlers

    cancelled = await user_handlers.cancel_subscription(callback.from_user.id)
    if callback.message:
        text = (
            "✅ Автоматическое продление отключено. Доступ сохранится до конца оплаченного периода."
            if cancelled
            else "Актуальной подписки с автопродлением не найдено."
        )
        await callback.message.answer(
            text,
            reply_markup=_subscription_keyboard(await is_admin(callback.from_user.id)),
        )
    await callback.answer("Автопродление отключено" if cancelled else "Подписка не найдена")


@router.message(Command("menu_editor"))
async def menu_editor(message: Message) -> None:
    if not await is_admin(message.from_user.id if message.from_user else None):
        await message.answer("Команда недоступна.")
        return
    await message.answer(
        "<b>Редактор пользовательского меню</b>\n\n"
        "Включайте и выключайте кнопки — изменения применяются сразу.",
        reply_markup=await _editor_markup(),
    )


@router.callback_query(F.data.startswith("menuedit:"))
async def menu_editor_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    action = callback.data.split(":")
    section = action[1] if len(action) > 1 else ""
    if section == "cancel":
        await state.clear()
        await callback.answer("Закрыто")
        return
    if section == "toggle" and len(action) == 3 and action[2] in BUTTONS:
        field = action[2]
        data = await get_menu_content()
        enabled = _is_enabled(data, field)
        await set_menu_content(field, "0" if enabled else "1")
        if callback.message:
            await callback.message.edit_reply_markup(reply_markup=await _editor_markup())
        await callback.answer(f"Кнопка «{BUTTONS[field]}» {'выключена' if enabled else 'включена'}")
        return
    if section == "preview":
        data = await get_menu_content()
        lines = [
            f"{'✅' if _is_enabled(data, field) else '❌'} {label}"
            for field, label in BUTTONS.items()
        ]
        text = (
            "<b>Текущие кнопки пользовательского меню</b>\n\n"
            + "\n".join(lines)
            + f"\n\n<b>Оферта:</b> {data['offer_url']}"
        )
        if callback.message:
            await callback.message.answer(text, reply_markup=await _editor_markup())
        await callback.answer()
        return
    state_map = {
        "settings": MenuEdit.settings,
        "offer": MenuEdit.offer,
        "instruction": MenuEdit.instruction,
    }
    target = state_map.get(section)
    if target is None:
        await callback.answer("Неизвестный раздел", show_alert=True)
        return
    await state.set_state(target)
    prompt = "Отправьте новый текст одним сообщением. HTML-разметка поддерживается."
    if section == "offer":
        prompt = "Отправьте новую полную HTTPS-ссылку оферты."
    if callback.message:
        await callback.message.answer(prompt)
    await callback.answer()


@router.message(MenuEdit.settings)
async def save_settings_text(message: Message, state: FSMContext) -> None:
    await _save_text(message, state, "settings")


@router.message(MenuEdit.instruction)
async def save_instruction_text(message: Message, state: FSMContext) -> None:
    await _save_text(message, state, "instruction")


@router.message(MenuEdit.offer)
async def save_offer_url(message: Message, state: FSMContext) -> None:
    value = (message.text or "").strip()
    if not value.startswith("https://"):
        await message.answer("Ссылка должна начинаться с https://")
        return
    await set_menu_content("offer_url", value)
    await state.clear()
    await message.answer("✅ Ссылка оферты сохранена.", reply_markup=await _editor_markup())


async def _save_text(message: Message, state: FSMContext, field: str) -> None:
    value = (message.text or "").strip()
    if not value:
        await message.answer("Текст не может быть пустым.")
        return
    await set_menu_content(field, value)
    await state.clear()
    await message.answer("✅ Изменения сохранены.", reply_markup=await _editor_markup())
