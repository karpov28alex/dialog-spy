from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from redis import Redis

from app.core.config import get_settings

settings = get_settings()
CONTENT_KEY = "dialog_spy:user_menu_content"
DEFAULT_OFFER_URL = "https://mooncloud.ltd/spy/terms.html#free"

DEFAULT_VISIBILITY = {
    "show_mini_app": True,
    "show_stats": True,
    "show_subscription": True,
    "show_profile": True,
    "show_settings": True,
    "show_instruction": True,
    "show_offer": True,
}


def _enabled(data: dict[str, str], key: str) -> bool:
    default = "1" if DEFAULT_VISIBILITY[key] else "0"
    return data.get(key, default) not in {"0", "false", "False", "off"}


def _menu_config() -> tuple[str, dict[str, bool]]:
    redis = Redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=1)
    try:
        data = redis.hgetall(CONTENT_KEY)
        offer_url = data.get("offer_url") or DEFAULT_OFFER_URL
        visibility = {key: _enabled(data, key) for key in DEFAULT_VISIBILITY}
        return offer_url, visibility
    except Exception:
        return DEFAULT_OFFER_URL, dict(DEFAULT_VISIBILITY)
    finally:
        redis.close()


def enhanced_user_keyboard(admin: bool = False) -> InlineKeyboardMarkup:
    """Return the single complete keyboard used by every user-facing screen."""
    offer_url, visibility = _menu_config()
    rows: list[list[InlineKeyboardButton]] = []

    if visibility["show_mini_app"]:
        rows.append([
            InlineKeyboardButton(text="📱 Открыть Mini App", web_app=WebAppInfo(url=settings.mini_app_url))
        ])
    if visibility["show_stats"]:
        rows.append([InlineKeyboardButton(text="📊 Статистика", callback_data="user:stats")])
    if visibility["show_subscription"]:
        rows.append([InlineKeyboardButton(text="💎 Подписка", callback_data="user:subscription")])

    profile_row: list[InlineKeyboardButton] = []
    if visibility["show_profile"]:
        profile_row.append(InlineKeyboardButton(text="👤 Профиль", callback_data="user:profile"))
    if visibility["show_settings"]:
        profile_row.append(InlineKeyboardButton(text="⚙️ Настройки", callback_data="user:settings"))
    if profile_row:
        rows.append(profile_row)

    if visibility["show_instruction"]:
        rows.append([InlineKeyboardButton(text="📖 Инструкция", callback_data="help")])
    if visibility["show_offer"]:
        rows.append([InlineKeyboardButton(text="📄 Оферта", url=offer_url)])
    if admin:
        rows.append([InlineKeyboardButton(text="🛡 Админ-панель", callback_data="crm:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
