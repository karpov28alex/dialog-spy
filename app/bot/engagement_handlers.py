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
    """Draw crisp emoji-like icons without relying on OS emoji fonts."""
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


async def _pulse(telegram_id: int) -> dict | None:
    now = datetime.utcnow()
    since = now - timedelta(hours=24)
    previous_since = since - timedelta(hours=24)
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

    delta = messages - previous
    trend = 0 if previous <= 0 else round(delta / previous * 100)
    top_name = "—"
    top_messages = 0
    if top:
        top_name = top.peer_name or (f"@{top.peer_username}" if top.peer_username else "Диалог")
        top_messages = int(top.n or 0)
    return {"messages": messages, "previous": previous, "trend": trend, "edited": edited, "deleted": deleted, "media": media, "protected": protected, "active_dialogs": active_dialogs, "top_name": top_name[:28], "top_messages": top_messages}


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
    d.text((72, 68), "PHANTOM PULSE", font=_font(25, True), fill="#b85cff")
    d.text((72, 112), "Что произошло за 24 часа", font=_font(48, True), fill="white")
    trend = data["trend"]
    trend_text = "новая активность" if data["previous"] == 0 and data["messages"] else f"{trend:+d}% к прошлым суткам"
    d.rounded_rectangle((858, 74, 1110, 130), 22, fill="#211033", outline="#512778", width=2)
    d.text((884, 88), trend_text[:23], font=_font(18, True), fill="#d9baff")

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
    d.text((848, 454), "Сохранено", font=_font(23, True), fill="#c36fff")
    d.text((804, 506), str(data["protected"]), font=_font(48, True), fill="white")
    d.text((874, 526), "скрытых медиа", font=_font(19), fill="#aaa0b8")
    d.text((804, 573), "Архив обновляется автоматически", font=_font(17), fill="#81768f")

    out = BytesIO()
    image.save(out, "PNG", optimize=True)
    return out.getvalue()


def _keyboard(admin: bool) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="✨ Обновить Pulse", callback_data="engagement:today")], [InlineKeyboardButton(text="💬 Диалоги", web_app=WebAppInfo(url=f"{settings.mini_app_url}?screen=dialogs")), InlineKeyboardButton(text="📊 Аналитика", web_app=WebAppInfo(url=f"{settings.mini_app_url}?screen=stats"))]]
    rows.extend([list(row) for row in enhanced_user_keyboard(admin).inline_keyboard])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _send(target: Message, telegram_id: int) -> None:
    data = await _pulse(telegram_id)
    admin = await is_admin(telegram_id)
    if data is None:
        await target.answer("Профиль ещё не создан. Отправьте /start.", reply_markup=enhanced_user_keyboard(admin))
        return
    facts = []
    if data["deleted"]:
        facts.append(f"🗑 За сутки удалили {data['deleted']} сообщений")
    if data["edited"]:
        facts.append(f"✏️ Изменили {data['edited']} сообщений")
    if data["top_messages"]:
        facts.append(f"🔥 Больше всего общения — {data['top_name']} ({data['top_messages']})")
    if not facts:
        facts.append("✨ День спокойный — Phantom продолжает следить за архивом")
    caption = "<b>👻 Phantom Pulse</b>\n\n" + "\n".join(facts[:3]) + "\n\n<blockquote>Откройте Mini App — там вся история и детали.</blockquote>"
    await target.answer_photo(BufferedInputFile(_render(data), filename="phantom-pulse.png"), caption=caption, reply_markup=_keyboard(admin))


@router.message(Command("today"))
async def today_command(message: Message) -> None:
    if message.from_user:
        await _send(message, message.from_user.id)


@router.callback_query(F.data.in_({"user:today", "engagement:today"}))
async def today_callback(callback: CallbackQuery) -> None:
    await callback.answer("Обновляю Pulse…")
    if callback.message:
        await _send(callback.message, callback.from_user.id)
