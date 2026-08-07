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


async def _pulse(telegram_id: int) -> dict | None:
    now = datetime.utcnow()
    since = now - timedelta(hours=24)
    previous_since = since - timedelta(hours=24)
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if not user:
            return None

        base = (
            select(DbMessage.id)
            .join(Dialog, Dialog.id == DbMessage.dialog_id)
            .where(Dialog.owner_user_id == user.id)
        )
        messages = int(await session.scalar(select(func.count()).select_from(base.where(DbMessage.sent_at >= since).subquery())) or 0)
        previous = int(
            await session.scalar(
                select(func.count()).select_from(
                    base.where(DbMessage.sent_at >= previous_since, DbMessage.sent_at < since).subquery()
                )
            )
            or 0
        )
        edited = int(
            await session.scalar(
                select(func.count(DbMessage.id))
                .join(Dialog, Dialog.id == DbMessage.dialog_id)
                .where(Dialog.owner_user_id == user.id, DbMessage.edited_at >= since)
            )
            or 0
        )
        deleted = int(
            await session.scalar(
                select(func.count(DbMessage.id))
                .join(Dialog, Dialog.id == DbMessage.dialog_id)
                .where(Dialog.owner_user_id == user.id, DbMessage.deleted_at >= since)
            )
            or 0
        )
        media = int(
            await session.scalar(
                select(func.count(Media.id))
                .join(DbMessage, DbMessage.id == Media.message_id)
                .join(Dialog, Dialog.id == DbMessage.dialog_id)
                .where(Dialog.owner_user_id == user.id, DbMessage.sent_at >= since)
            )
            or 0
        )
        active_dialogs = int(
            await session.scalar(
                select(func.count(distinct(DbMessage.dialog_id)))
                .join(Dialog, Dialog.id == DbMessage.dialog_id)
                .where(Dialog.owner_user_id == user.id, DbMessage.sent_at >= since)
            )
            or 0
        )
        top = (
            await session.execute(
                select(Dialog.peer_name, Dialog.peer_username, func.count(DbMessage.id).label("n"))
                .join(DbMessage, DbMessage.dialog_id == Dialog.id)
                .where(Dialog.owner_user_id == user.id, DbMessage.sent_at >= since)
                .group_by(Dialog.id, Dialog.peer_name, Dialog.peer_username)
                .order_by(func.count(DbMessage.id).desc())
                .limit(1)
            )
        ).first()
        protected = int(
            await session.scalar(
                select(func.count(Media.id))
                .join(DbMessage, DbMessage.id == Media.message_id)
                .join(Dialog, Dialog.id == DbMessage.dialog_id)
                .where(Dialog.owner_user_id == user.id, DbMessage.sent_at >= since, Media.is_protected.is_(True))
            )
            or 0
        )

    delta = messages - previous
    trend = 0 if previous <= 0 else round(delta / previous * 100)
    top_name = "—"
    top_messages = 0
    if top:
        top_name = top.peer_name or (f"@{top.peer_username}" if top.peer_username else "Диалог")
        top_messages = int(top.n or 0)
    return {
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
    d.text((72, 68), "PHANTOM PULSE", font=_font(25, True), fill="#b85cff")
    d.text((72, 112), "Что произошло за 24 часа", font=_font(48, True), fill="white")
    trend = data["trend"]
    trend_text = "новая активность" if data["previous"] == 0 and data["messages"] else f"{trend:+d}% к прошлым суткам"
    d.rounded_rectangle((858, 74, 1110, 130), 22, fill="#211033", outline="#512778", width=2)
    d.text((884, 88), trend_text[:23], font=_font(18, True), fill="#d9baff")

    metrics = [
        ("СООБЩЕНИЯ", data["messages"], "💬"),
        ("ИЗМЕНЕНО", data["edited"], "✏"),
        ("УДАЛЕНО", data["deleted"], "×"),
        ("МЕДИА", data["media"], "▣"),
    ]
    xs = [72, 342, 612, 882]
    for x, (label, value, icon) in zip(xs, metrics, strict=True):
        d.rounded_rectangle((x, 208, x + 232, 388), 30, fill="#151022", outline="#3b205c", width=2)
        d.text((x + 24, 231), icon, font=_font(30, True), fill="#bd6cff")
        d.text((x + 24, 280), f"{value:,}".replace(",", " "), font=_font(45, True), fill="white")
        d.text((x + 24, 342), label, font=_font(17, True), fill="#9b90aa")

    d.rounded_rectangle((72, 430, 748, 618), 30, fill="#120d1f", outline="#3a2154", width=2)
    d.text((98, 454), "🔥 Главный диалог", font=_font(23, True), fill="#c36fff")
    d.text((98, 500), data["top_name"], font=_font(34, True), fill="white")
    d.text((98, 552), f"{data['top_messages']} сообщений · {data['active_dialogs']} активных диалогов", font=_font(21), fill="#aaa0b8")

    d.rounded_rectangle((778, 430, 1110, 618), 30, fill="#120d1f", outline="#3a2154", width=2)
    d.text((804, 454), "👻 Сохранено", font=_font(23, True), fill="#c36fff")
    d.text((804, 506), str(data["protected"]), font=_font(48, True), fill="white")
    d.text((874, 526), "скрытых медиа", font=_font(19), fill="#aaa0b8")
    d.text((804, 573), "Архив обновляется автоматически", font=_font(17), fill="#81768f")

    out = BytesIO()
    image.save(out, "PNG", optimize=True)
    return out.getvalue()


def _keyboard(admin: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="✨ Обновить Pulse", callback_data="engagement:today")],
        [
            InlineKeyboardButton(text="💬 Диалоги", web_app=WebAppInfo(url=f"{settings.mini_app_url}?screen=dialogs")),
            InlineKeyboardButton(text="📊 Аналитика", web_app=WebAppInfo(url=f"{settings.mini_app_url}?screen=stats")),
        ],
    ]
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
    await target.answer_photo(
        BufferedInputFile(_render(data), filename="phantom-pulse.png"),
        caption=caption,
        reply_markup=_keyboard(admin),
    )


@router.message(Command("today"))
async def today_command(message: Message) -> None:
    if message.from_user:
        await _send(message, message.from_user.id)


@router.callback_query(F.data.in_({"user:today", "engagement:today"}))
async def today_callback(callback: CallbackQuery) -> None:
    await callback.answer("Обновляю Pulse…")
    if callback.message:
        await _send(callback.message, callback.from_user.id)
