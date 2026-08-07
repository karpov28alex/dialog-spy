from __future__ import annotations

from datetime import datetime, timedelta
from io import BytesIO

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from sqlalchemy import distinct, func, select

from app.bot.admin_console import is_admin
from app.bot.enhanced_user_menu import enhanced_user_keyboard
from app.core.config import get_settings
from app.db.models import Dialog, Media, Message as DbMessage, User
from app.db.session import SessionLocal
from app.services.users import referral_code

router = Router(name="engagement")
settings = get_settings()


def _font(size: int, bold: bool = False):
    candidates = (
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    )
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_icon(d: ImageDraw.ImageDraw, kind: str, x: int, y: int, size: int = 34) -> None:
    if kind == "chat":
        d.rounded_rectangle((x, y, x + size, y + size - 7), 9, fill="#b85cff")
        d.polygon(((x + 8, y + size - 9), (x + 5, y + size + 2), (x + 17, y + size - 8)), fill="#b85cff")
        for dx in (9, 17, 25):
            d.ellipse((x + dx - 2, y + 12, x + dx + 2, y + 16), fill="#ffffff")
    elif kind == "edit":
        d.line((x + 6, y + size - 5, x + size - 6, y + 5), fill="#ffd45c", width=8)
        d.line((x + 9, y + size - 8, x + size - 9, y + 8), fill="#ff9f43", width=3)
        d.polygon(((x + 2, y + size + 1), (x + 7, y + size - 10), (x + 13, y + size - 4)), fill="#e8d6bd")
    elif kind == "trash":
        d.rounded_rectangle((x + 7, y + 10, x + size - 5, y + size), 5, fill="#9ca3af", outline="#d9dce3", width=2)
        d.rectangle((x + 4, y + 5, x + size - 2, y + 10), fill="#c8ccd4")
        d.rectangle((x + 12, y + 1, x + size - 10, y + 5), fill="#c8ccd4")
        d.line((x + 14, y + 15, x + 14, y + size - 5), fill="#5f6672", width=2)
        d.line((x + 22, y + 15, x + 22, y + size - 5), fill="#5f6672", width=2)
    elif kind == "media":
        d.rounded_rectangle((x + 2, y + 7, x + size, y + size - 2), 6, fill="#7c3aed", outline="#d8b4fe", width=2)
        d.ellipse((x + 11, y + 13, x + 25, y + 27), fill="#111827", outline="#f5f3ff", width=2)
        d.ellipse((x + 16, y + 18, x + 20, y + 22), fill="#ffffff")
        d.rectangle((x + 8, y + 3, x + 16, y + 8), fill="#f59e0b")
    elif kind == "fire":
        d.ellipse((x + 7, y + 8, x + size - 5, y + size), fill="#ff6b2c")
        d.polygon(((x + 8, y + 23), (x + 18, y - 2), (x + 22, y + 17), (x + size - 4, y + 8), (x + size - 7, y + 29)), fill="#ff8a1f")
        d.ellipse((x + 14, y + 19, x + size - 10, y + size - 2), fill="#ffd54a")
    elif kind == "ghost":
        d.ellipse((x + 5, y + 2, x + size - 3, y + 29), fill="#f3f4f6")
        d.rectangle((x + 5, y + 16, x + size - 3, y + 29), fill="#f3f4f6")
        d.polygon(((x + 5, y + 27), (x + 10, y + size), (x + 16, y + 27), (x + 22, y + size), (x + 28, y + 27), (x + size - 3, y + size)), fill="#f3f4f6")
        d.ellipse((x + 11, y + 11, x + 15, y + 16), fill="#4c1d95")
        d.ellipse((x + 22, y + 11, x + 26, y + 16), fill="#4c1d95")


def _streak(days: list[datetime]) -> int:
    active = {item.date() for item in days}
    if not active:
        return 0
    cursor = max(active)
    total = 0
    while cursor in active:
        total += 1
        cursor -= timedelta(days=1)
    return total


async def _recap(telegram_id: int, *, days: int) -> dict | None:
    now = datetime.utcnow()
    since = now - timedelta(days=days)
    previous_since = since - timedelta(days=days)
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if not user:
            return None
        base = select(DbMessage.id).join(Dialog, Dialog.id == DbMessage.dialog_id).where(Dialog.owner_user_id == user.id)
        messages = int(await session.scalar(select(func.count()).select_from(base.where(DbMessage.sent_at >= since).subquery())) or 0)
        previous = int(await session.scalar(select(func.count()).select_from(base.where(DbMessage.sent_at >= previous_since, DbMessage.sent_at < since).subquery())) or 0)
        edited = int(await session.scalar(select(func.count(DbMessage.id)).join(Dialog, Dialog.id == DbMessage.dialog_id).where(Dialog.owner_user_id == user.id, DbMessage.edited_at >= since)) or 0)
        deleted = int(await session.scalar(select(func.count(DbMessage.id)).join(Dialog, Dialog.id == DbMessage.dialog_id).where(Dialog.owner_user_id == user.id, DbMessage.deleted_at >= since)) or 0)
        media = int(await session.scalar(select(func.count(Media.id)).join(DbMessage, DbMessage.id == Media.message_id).join(Dialog, Dialog.id == DbMessage.dialog_id).where(Dialog.owner_user_id == user.id, DbMessage.sent_at >= since)) or 0)
        active_dialogs = int(await session.scalar(select(func.count(distinct(DbMessage.dialog_id))).join(Dialog, Dialog.id == DbMessage.dialog_id).where(Dialog.owner_user_id == user.id, DbMessage.sent_at >= since)) or 0)
        top = (await session.execute(select(Dialog.peer_name, Dialog.peer_username, func.count(DbMessage.id).label("n")).join(DbMessage, DbMessage.dialog_id == Dialog.id).where(Dialog.owner_user_id == user.id, DbMessage.sent_at >= since).group_by(Dialog.id, Dialog.peer_name, Dialog.peer_username).order_by(func.count(DbMessage.id).desc()).limit(1))).first()
        protected = int(await session.scalar(select(func.count(Media.id)).join(DbMessage, DbMessage.id == Media.message_id).join(Dialog, Dialog.id == DbMessage.dialog_id).where(Dialog.owner_user_id == user.id, DbMessage.sent_at >= since, Media.is_protected.is_(True))) or 0)
        recent_days = list(await session.scalars(select(DbMessage.sent_at).join(Dialog, Dialog.id == DbMessage.dialog_id).where(Dialog.owner_user_id == user.id, DbMessage.sent_at >= now - timedelta(days=45)).order_by(DbMessage.sent_at.desc())))
        code = referral_code(user)

    trend = 0 if previous <= 0 else round((messages - previous) / previous * 100)
    top_name = "—"
    top_messages = 0
    if top:
        top_name = top.peer_name or (f"@{top.peer_username}" if top.peer_username else "Диалог")
        top_messages = int(top.n or 0)
    return {
        "days": days,
        "messages": messages,
        "previous": previous,
        "trend": trend,
        "edited": edited,
        "deleted": deleted,
        "media": media,
        "protected": protected,
        "active_dialogs": active_dialogs,
        "top_name": top_name[:28],
        "top_messages": top_messages,
        "streak": _streak(recent_days),
        "referral_url": f"https://t.me/{settings.telegram_bot_username}?start=ref_{code}",
    }


def _render(data: dict) -> bytes:
    w, h = 1200, 720
    image = Image.new("RGB", (w, h), "#05030d")
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((-180, -230, 610, 560), fill=(121, 27, 236, 185))
    gd.ellipse((700, 180, 1420, 900), fill=(70, 20, 155, 135))
    glow = glow.filter(ImageFilter.GaussianBlur(120))
    image.paste(glow, (0, 0), glow)
    d = ImageDraw.Draw(image)
    d.rounded_rectangle((36, 34, 1164, 686), 46, fill="#0d0819", outline="#7d2cff", width=3)
    kicker = "PHANTOM DAILY" if data["days"] == 1 else "PHANTOM WEEKLY"
    title = "Что произошло за 24 часа" if data["days"] == 1 else "Ваша неделя в Phantom"
    d.text((72, 68), kicker, font=_font(25, True), fill="#b85cff")
    d.text((72, 112), title, font=_font(48, True), fill="white")
    trend_text = "новая активность" if data["previous"] == 0 and data["messages"] else f"{data['trend']:+d}% к прошлому периоду"
    d.rounded_rectangle((842, 74, 1110, 130), 22, fill="#211033", outline="#512778", width=2)
    d.text((864, 88), trend_text[:25], font=_font(18, True), fill="#d9baff")
    metrics = [("СООБЩЕНИЯ", data["messages"], "chat"), ("ИЗМЕНЕНО", data["edited"], "edit"), ("УДАЛЕНО", data["deleted"], "trash"), ("МЕДИА", data["media"], "media")]
    xs = [72, 342, 612, 882]
    for x, (label, value, icon) in zip(xs, metrics, strict=True):
        d.rounded_rectangle((x, 208, x + 232, 388), 30, fill="#151022", outline="#3b205c", width=2)
        _draw_icon(d, icon, x + 24, 229, 34)
        d.text((x + 24, 280), f"{value:,}".replace(",", " "), font=_font(45, True), fill="white")
        d.text((x + 24, 342), label, font=_font(17, True), fill="#9b90aa")
    d.rounded_rectangle((72, 430, 748, 618), 30, fill="#120d1f", outline="#3a2154", width=2)
    _draw_icon(d, "fire", 98, 450, 34)
    d.text((142, 454), "Главный диалог", font=_font(23, True), fill="#c36fff")
    d.text((98, 500), data["top_name"], font=_font(34, True), fill="white")
    d.text((98, 552), f"{data['top_messages']} сообщений · {data['active_dialogs']} активных диалогов", font=_font(21), fill="#aaa0b8")
    d.rounded_rectangle((778, 430, 1110, 618), 30, fill="#120d1f", outline="#3a2154", width=2)
    _draw_icon(d, "ghost", 804, 450, 34)
    d.text((848, 454), "Серия активности", font=_font(23, True), fill="#c36fff")
    d.text((804, 505), str(data["streak"]), font=_font(48, True), fill="white")
    d.text((870, 526), "дней подряд", font=_font(19), fill="#aaa0b8")
    d.text((804, 573), f"Скрытых медиа: {data['protected']}", font=_font(17), fill="#81768f")
    out = BytesIO()
    image.save(out, "PNG", optimize=True)
    return out.getvalue()


def _keyboard(admin: bool, *, days: int, share: bool = False) -> InlineKeyboardMarkup:
    if share:
        return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👻 Получить свою статистику", url="https://t.me/" + settings.telegram_bot_username)]])
    other = 7 if days == 1 else 1
    other_text = "📅 Итоги недели" if days == 1 else "☀️ Сегодня"
    rows = [
        [InlineKeyboardButton(text="✨ Обновить", callback_data=f"engagement:recap:{days}"), InlineKeyboardButton(text=other_text, callback_data=f"engagement:recap:{other}")],
        [InlineKeyboardButton(text="🚀 Поделиться", callback_data=f"engagement:share:{days}")],
        [InlineKeyboardButton(text="💬 Диалоги", web_app=WebAppInfo(url=f"{settings.mini_app_url}?screen=dialogs")), InlineKeyboardButton(text="📊 Аналитика", web_app=WebAppInfo(url=f"{settings.mini_app_url}?screen=stats"))],
    ]
    rows.extend([list(row) for row in enhanced_user_keyboard(admin).inline_keyboard])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _caption(data: dict, *, shared: bool = False) -> str:
    period = "сегодня" if data["days"] == 1 else "за неделю"
    facts = []
    if data["streak"] > 1:
        facts.append(f"🔥 Серия активности: <b>{data['streak']} дней</b>")
    if data["deleted"]:
        facts.append(f"🗑 Удалено: <b>{data['deleted']}</b>")
    if data["edited"]:
        facts.append(f"✏️ Изменено: <b>{data['edited']}</b>")
    if data["top_messages"]:
        facts.append(f"💜 Главный диалог — <b>{data['top_name']}</b> ({data['top_messages']})")
    if not facts:
        facts.append("✨ Спокойный период — архив продолжает обновляться")
    if shared:
        return (
            f"<b>👻 Моя статистика Phantom {period}</b>\n\n"
            + "\n".join(facts[:4])
            + f"\n\nХочешь увидеть, кто чаще пишет, удаляет и меняет сообщения у тебя?\n👉 {data['referral_url']}"
        )
    return f"<b>👻 Phantom {'Daily' if data['days'] == 1 else 'Weekly'}</b>\n\n" + "\n".join(facts[:4]) + "\n\n<blockquote>Открой Mini App — там вся история и детали.</blockquote>"


async def _send(target: Message, telegram_id: int, *, days: int = 1, shared: bool = False) -> None:
    data = await _recap(telegram_id, days=days)
    admin = await is_admin(telegram_id)
    if data is None:
        await target.answer("Профиль ещё не создан. Отправьте /start.", reply_markup=enhanced_user_keyboard(admin))
        return
    filename = "phantom-daily.png" if days == 1 else "phantom-weekly.png"
    await target.answer_photo(BufferedInputFile(_render(data), filename=filename), caption=_caption(data, shared=shared), reply_markup=_keyboard(admin, days=days, share=shared))


@router.message(Command("today"))
async def today_command(message: Message) -> None:
    if message.from_user:
        await _send(message, message.from_user.id, days=1)


@router.message(Command("week", "weekly"))
async def week_command(message: Message) -> None:
    if message.from_user:
        await _send(message, message.from_user.id, days=7)


@router.callback_query(F.data.in_({"user:today", "engagement:today"}))
async def today_callback(callback: CallbackQuery) -> None:
    await callback.answer("Обновляю Daily…")
    if callback.message:
        await _send(callback.message, callback.from_user.id, days=1)


@router.callback_query(F.data.startswith("engagement:recap:"))
async def recap_callback(callback: CallbackQuery) -> None:
    days = 7 if callback.data and callback.data.endswith(":7") else 1
    await callback.answer("Собираю итоги…")
    if callback.message:
        await _send(callback.message, callback.from_user.id, days=days)


@router.callback_query(F.data.startswith("engagement:share:"))
async def share_callback(callback: CallbackQuery) -> None:
    days = 7 if callback.data and callback.data.endswith(":7") else 1
    await callback.answer("Готовлю карточку для пересылки…")
    if callback.message:
        await _send(callback.message, callback.from_user.id, days=days, shared=True)
