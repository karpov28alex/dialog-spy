from __future__ import annotations

from aiogram import F, Router
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)

from app.bot.admin_console import is_admin
from app.bot.enhanced_user_menu import enhanced_user_keyboard
from app.bot.statistics_card_handlers import _collect_stats, _leader_avatars
from app.bot.statistics_card_v2_handlers import _render
from app.core.config import get_settings

router = Router(name="statistics-share-card")
settings = get_settings()


def referral_link(telegram_id: int) -> str:
    username = settings.telegram_bot_username.lstrip("@")
    return f"https://t.me/{username}?start=ref_{telegram_id}"


def stats_keyboard(admin: bool) -> InlineKeyboardMarkup:
    rows = [list(row) for row in enhanced_user_keyboard(admin).inline_keyboard]
    rows.insert(
        1,
        [
            InlineKeyboardButton(
                text="📲 Открыть статистику",
                web_app=WebAppInfo(url=settings.mini_app_url),
            )
        ],
    )
    rows.extend(
        [
            [InlineKeyboardButton(text="🚀 Поделиться результатом", callback_data="product:share_card")],
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="product:stats")],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def share_caption(stats: dict, telegram_id: int) -> str:
    totals = stats["totals"]
    link = referral_link(telegram_id)
    return (
        "<b>📊 Вот что сохранил мой Phantom</b>\n\n"
        f"💬 <b>{totals['messages']:,}</b> сообщений\n"
        f"✏️ <b>{totals['edited']:,}</b> изменений\n"
        f"🗑 <b>{totals['deleted']:,}</b> удалений\n"
        f"👻 <b>{totals['protected']:,}</b> скрытых медиа\n\n"
        "Интересно, какие люди, часы и диалоги лидируют у тебя? "
        "Подключи Phantom — он соберёт твою личную статистику общения.\n\n"
        f"👉 <a href=\"{link}\">Получить свою статистику</a>"
    )


@router.callback_query(F.data == "product:share_card")
async def share_statistics_card(callback: CallbackQuery) -> None:
    await callback.answer("Готовлю карточку для пересылки…")
    if callback.message is None:
        return
    stats = await _collect_stats(callback.from_user.id)
    if stats is None:
        link = referral_link(callback.from_user.id)
        await callback.message.answer(
            "<b>📊 Статистика пока собирается</b>\n\n"
            "Подключите Phantom, затем снова нажмите «Поделиться».\n\n"
            f"👉 <a href=\"{link}\">Открыть Phantom</a>"
        )
        return
    avatars = await _leader_avatars(stats)
    card = BufferedInputFile(_render(stats, avatars), filename="phantom-share-statistics.png")
    link = referral_link(callback.from_user.id)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👻 Получить свою статистику", url=link)],
        ]
    )
    await callback.message.answer_photo(
        card,
        caption=share_caption(stats, callback.from_user.id),
        reply_markup=keyboard,
    )
    await callback.message.answer(
        "↗️ <b>Карточка готова.</b> Перешлите сообщение выше другу — "
        "фото, описание и персональная ссылка сохранятся вместе.",
        reply_markup=enhanced_user_keyboard(await is_admin(callback.from_user.id)),
    )
