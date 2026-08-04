from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from app.bot.admin_console import is_admin, user_menu
from app.bot.statistics_card_handlers import _collect_stats, _leader_avatars
from app.bot.statistics_card_v2_handlers import _render
from app.core.config import get_settings
from app.db.models import User
from app.db.session import SessionLocal
from app.services.access import access_state, get_monetization_settings
from app.services.access_funnel import channel_gate_passed, get_funnel_config
from app.services.users import activate_trial_after_channel, has_active_business

router = Router(name="product-experience")
settings = get_settings()


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    paths = (
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    )
    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _welcome_cover() -> bytes:
    image = Image.new("RGB", (1200, 675), "#05030c")
    glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((620, -300, 1450, 550), fill="#6f18cc")
    gd.ellipse((-350, 300, 520, 980), fill="#28114d")
    glow = glow.filter(ImageFilter.GaussianBlur(145))
    image.paste(glow, (0, 0), glow)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((30, 30, 1170, 645), 42, outline="#7d2bd1", width=3)

    # Compact Phantom mark inspired by the product logo.
    draw.arc((710, 95, 1040, 425), 270, 88, fill="#9a35ff", width=72)
    draw.polygon(((745, 315), (925, 420), (730, 555)), fill="#7623e3")
    draw.polygon(((690, 180), (895, 145), (1020, 235), (805, 270)), fill="#982fff")
    draw.polygon(((716, 148), (895, 125), (945, 185), (740, 215)), fill="#a33cff")
    draw.polygon(((760, 295), (828, 318), (790, 342)), fill="white")
    draw.polygon(((900, 310), (965, 286), (935, 337)), fill="white")

    draw.text((82, 105), "PHANTOM", font=_font(70, True), fill="white")
    draw.text((85, 205), "Архив Telegram Business", font=_font(34), fill="#b9a9c9")
    draw.text((85, 350), "Сообщения не исчезают.", font=_font(42, True), fill="white")
    draw.text((85, 414), "Правки не теряются.", font=_font(42, True), fill="white")
    draw.text((85, 478), "История остаётся вашей.", font=_font(42, True), fill="#bd68ff")
    draw.text((86, 580), "PRIVATE · AUTOMATIC · SECURE", font=_font(19, True), fill="#7f718c")
    output = BytesIO()
    image.save(output, "JPEG", quality=92, optimize=True)
    return output.getvalue()


async def branded_send_access_screen(message: Message, user: User) -> None:
    """Drop-in replacement for access_funnel.send_access_screen.

    It preserves the existing access funnel and changes only the successful
    product presentation shown after all gates have passed.
    """
    config = await get_funnel_config()
    channel_ok = not config.channel_required or await channel_gate_passed(
        __import__("app.bot.setup", fromlist=["bot"]).bot,
        user_id=user.telegram_id,
        config=config,
    )
    if config.enabled and not channel_ok:
        from app.bot.access_funnel import subscription_keyboard

        await message.answer(
            config.subscription_text,
            reply_markup=subscription_keyboard(config.channel_url),
        )
        return

    async with SessionLocal() as session, session.begin():
        db_user = await session.get(User, user.id, with_for_update=True)
        if db_user:
            started = await activate_trial_after_channel(session, user=db_user)
            business_connected = await has_active_business(session, db_user.id)
            state = await access_state(session, db_user)
            referral_available = db_user.referral_bonus_granted_at is None
            monetization = await get_monetization_settings(session)
        else:
            started = False
            business_connected = False
            state = await access_state(session, user)
            referral_available = user.referral_bonus_granted_at is None
            monetization = await get_monetization_settings(session)

    if started:
        await message.answer(config.trial_started_text.format(days=monetization.trial_days))
    if config.enabled and config.business_required and not business_connected and not state.active:
        await message.answer(config.business_required_text)
        return
    if config.enabled and not state.active:
        from app.bot.access_funnel import expired_keyboard

        referral_available = config.referral_required and referral_available
        text = config.referral_text if referral_available else config.payment_required_text
        await message.answer(
            text,
            reply_markup=expired_keyboard(
                config.payment_url,
                config.payment_button_text,
                referral_available,
            ),
        )
        return

    caption = (
        "<b>👋 Добро пожаловать в Phantom</b>\n\n"
        "✏️ Правки, удаления и история сообщений.\n"
        "📸 Исчезающие фото, видео и голосовые.\n"
        "🕵️ Приватный просмотр и защищённый архив.\n\n"
        "<blockquote>🔐 Мы не получаем доступ к вашему аккаунту. "
        "Подключение управляется в настройках Telegram Business.</blockquote>\n\n"
        "👇 <b>Откройте Mini App и проверьте свой архив.</b>"
    )
    await message.answer_photo(
        BufferedInputFile(_welcome_cover(), filename="phantom-welcome.jpg"),
        caption=caption,
        reply_markup=user_menu(await is_admin(user.telegram_id)),
    )


def _stats_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📲 Открыть статистику", web_app=WebAppInfo(url=settings.mini_app_url))],
            [InlineKeyboardButton(text="🚀 Поделиться результатом", switch_inline_query="Моя статистика Phantom")],
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="product:stats")],
        ]
    )


async def _shareable_stats(message: Message, telegram_id: int) -> None:
    status = await message.answer("✨ Собираю персональные факты и лидеров общения…")
    stats = await _collect_stats(telegram_id)
    if stats is None:
        await status.edit_text("Профиль ещё не создан. Отправьте /start.")
        return
    avatars = await _leader_avatars(stats)
    card = BufferedInputFile(_render(stats, avatars), filename="phantom-my-year.png")
    totals = stats["totals"]
    caption = (
        "<b>📊 Мой цифровой архив Phantom</b>\n\n"
        f"💬 <b>{totals['messages']:,}</b> сообщений\n"
        f"✏️ <b>{totals['edited']:,}</b> изменений\n"
        f"🗑 <b>{totals['deleted']:,}</b> удалений\n"
        f"👻 <b>{totals['protected']:,}</b> скрытых медиа\n\n"
        "<blockquote>История общения говорит больше, чем кажется.</blockquote>\n"
        f"Обновлено: {datetime.now(UTC).strftime('%d.%m.%Y · %H:%M')} UTC"
    )
    await status.delete()
    await message.answer_photo(card, caption=caption, reply_markup=_stats_keyboard())


@router.message(Command("stats"))
async def stats_command(message: Message) -> None:
    if message.from_user:
        await _shareable_stats(message, message.from_user.id)


@router.callback_query(F.data.in_({"user:stats", "product:stats"}))
async def stats_callback(callback: CallbackQuery) -> None:
    await callback.answer("Формирую карточку…")
    if callback.message:
        await _shareable_stats(callback.message, callback.from_user.id)
