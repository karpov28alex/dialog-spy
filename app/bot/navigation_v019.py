from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from app.bot import user_handlers
from app.bot.enhanced_user_menu import subscription_commerce_config
from app.bot.screen_manager import replace_callback
from app.core.config import get_settings
from app.services.dialog_insights import dialog_insights, format_dialog_insights

router = Router(name="navigation-v019")
settings = get_settings()


def profile_keyboard(admin: bool = False) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="📱 Открыть Mini App", web_app=WebAppInfo(url=settings.mini_app_url))], [InlineKeyboardButton(text="📊 Статистика", callback_data="v019:stats")], [InlineKeyboardButton(text="⚙️ Настройки", callback_data="v019:settings")], [InlineKeyboardButton(text="📖 Инструкция", callback_data="v019:help")]]
    if admin: rows.append([InlineKeyboardButton(text="🛡 Админ-панель", callback_data="crm:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_profile(*rows: list[InlineKeyboardButton]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[*rows, [InlineKeyboardButton(text="↩️ Вернуться в профиль", callback_data="v019:profile")]])


async def _replace(callback: CallbackQuery) -> None:
    await replace_callback(callback)


@router.callback_query(F.data.in_({"user:profile", "v019:profile"}))
async def profile(callback: CallbackQuery) -> None:
    from app.bot.profile_card_handlers import _send_profile
    await callback.answer(); await _replace(callback)
    if callback.message:
        import app.bot.profile_card_handlers as profile_module
        original = profile_module._profile_keyboard; profile_module._profile_keyboard = lambda: profile_keyboard(False)
        try: await _send_profile(callback.message, callback.from_user.id)
        finally: profile_module._profile_keyboard = original


@router.callback_query(F.data.in_({"user:stats", "v019:stats"}))
async def stats(callback: CallbackQuery) -> None:
    from app.bot.product_experience_handlers import _shareable_stats
    import app.bot.product_experience_handlers as stats_module
    await callback.answer("Собираю статистику…"); await _replace(callback)
    if callback.message:
        original = stats_module._stats_keyboard
        stats_module._stats_keyboard = lambda admin: back_profile([InlineKeyboardButton(text="☀️ Сегодня", callback_data="engagement:recap:1"), InlineKeyboardButton(text="📅 7 дней", callback_data="engagement:recap:7")], [InlineKeyboardButton(text="🧠 Insights", callback_data="v019:insights")], [InlineKeyboardButton(text="📲 Открыть статистику", web_app=WebAppInfo(url=f"{settings.mini_app_url}?screen=stats"))], [InlineKeyboardButton(text="🚀 Поделиться", callback_data="product:share_card")])
        try: await _shareable_stats(callback.message, callback.from_user.id)
        finally: stats_module._stats_keyboard = original


@router.callback_query(F.data == "v019:insights")
async def insights(callback: CallbackQuery) -> None:
    await callback.answer("Анализирую диалоги…"); await _replace(callback)
    if not callback.message: return
    data = await dialog_insights(callback.from_user.id, 30)
    text = format_dialog_insights(data) if data else "Статистика ещё не накоплена."
    await callback.message.answer(text, reply_markup=back_profile([InlineKeyboardButton(text="📊 К статистике", callback_data="v019:stats")]))


@router.callback_query(F.data.in_({"user:settings", "v019:settings"}))
async def settings_screen(callback: CallbackQuery) -> None:
    await callback.answer(); prefs = await user_handlers._settings(callback.from_user.id)
    if not callback.message or not prefs: return
    await _replace(callback); enabled, _ = subscription_commerce_config(); base = user_handlers.settings_keyboard(prefs)
    rows = [list(row) for row in base.inline_keyboard if not any(button.callback_data == "user:menu" for button in row)]
    if enabled: rows.append([InlineKeyboardButton(text="💎 Подписка", callback_data="v019:subscription")])
    rows.append([InlineKeyboardButton(text="↩️ Вернуться в профиль", callback_data="v019:profile")])
    await callback.message.answer("<b>⚙️ Настройки</b>\n\nИзменения применяются сразу.", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@router.callback_query(F.data == "v019:subscription")
async def subscription_screen(callback: CallbackQuery) -> None:
    enabled, offer_url = subscription_commerce_config()
    if not enabled: await callback.answer("Раздел подписки отключён", show_alert=True); return
    await callback.answer(); await _replace(callback)
    if callback.message:
        text = await user_handlers._subscription_text(callback.from_user.id)
        await callback.message.answer(text, reply_markup=back_profile([InlineKeyboardButton(text="📄 Оферта", url=offer_url)], [InlineKeyboardButton(text="🚫 Отключить автопродление", callback_data="user:subscription:cancel")]))


@router.callback_query(F.data.in_({"help", "v019:help"}))
async def help_screen(callback: CallbackQuery) -> None:
    from app.bot.instruction_publisher import send_public_instruction
    await callback.answer(); await _replace(callback)
    if callback.message: await send_public_instruction(callback.message)
