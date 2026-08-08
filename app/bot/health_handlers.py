from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.admin_console import is_admin
from app.services.system_health import format_health, health_snapshot

router = Router(name="health-dashboard")


@router.callback_query(F.data == "health:show")
async def show_health(callback: CallbackQuery) -> None:
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer("Проверяю систему…")
    if callback.message:
        data = await health_snapshot()
        await callback.message.answer(
            format_health(data),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Обновить", callback_data="health:show")],
                [InlineKeyboardButton(text="◀️ Центр управления", callback_data="crm:home")],
            ]),
        )
