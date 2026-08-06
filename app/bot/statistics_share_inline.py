from __future__ import annotations

from aiogram import F, Router
from aiogram.types import (
    BufferedInputFile,
    InlineQuery,
    InlineQueryResultArticle,
    InlineQueryResultCachedPhoto,
    InputTextMessageContent,
)

from app.bot.statistics_card_handlers import _collect_stats, _leader_avatars
from app.bot.statistics_card_v2_handlers import _render
from app.core.config import get_settings

router = Router(name="statistics-share-inline")
settings = get_settings()


def _referral_link(telegram_id: int) -> str:
    username = settings.telegram_bot_username.lstrip("@")
    return f"https://t.me/{username}?start=ref_{telegram_id}"


def _share_caption(stats: dict, telegram_id: int) -> str:
    totals = stats["totals"]
    link = _referral_link(telegram_id)
    return (
        "📊 <b>Моя статистика в Phantom</b>\n\n"
        f"💬 {totals['messages']:,} сообщений · "
        f"✏️ {totals['edited']:,} изменений · "
        f"🗑 {totals['deleted']:,} удалений\n\n"
        "Посмотри, что расскажет твоя история общения — "
        "подключение занимает меньше минуты.\n"
        f"👉 {link}"
    )


@router.inline_query(F.query.startswith("Моя статистика Phantom"))
async def share_statistics_inline(query: InlineQuery) -> None:
    stats = await _collect_stats(query.from_user.id)
    if stats is None:
        link = _referral_link(query.from_user.id)
        await query.answer(
            [
                InlineQueryResultArticle(
                    id="phantom-stats-empty",
                    title="Статистика ещё не собрана",
                    description="Подключите Phantom и попробуйте снова",
                    input_message_content=InputTextMessageContent(
                        message_text=(
                            "📊 Моя статистика Phantom пока собирается.\n\n"
                            "Подключи свой архив и посмотри личные итоги:\n"
                            f"{link}"
                        )
                    ),
                )
            ],
            cache_time=5,
            is_personal=True,
        )
        return

    avatars = await _leader_avatars(stats)
    caption = _share_caption(stats, query.from_user.id)
    temporary = await query.bot.send_photo(
        chat_id=query.from_user.id,
        photo=BufferedInputFile(_render(stats, avatars), filename="phantom-statistics.png"),
        caption=caption,
    )
    photo = temporary.photo[-1] if temporary.photo else None
    try:
        await query.bot.delete_message(query.from_user.id, temporary.message_id)
    except Exception:
        pass

    if photo is None:
        await query.answer([], cache_time=1, is_personal=True)
        return

    await query.answer(
        [
            InlineQueryResultCachedPhoto(
                id=f"phantom-stats-{query.from_user.id}",
                photo_file_id=photo.file_id,
                title="Поделиться статистикой Phantom",
                description="Фото, краткий итог и персональная ссылка",
                caption=caption,
                parse_mode="HTML",
            )
        ],
        cache_time=30,
        is_personal=True,
    )
