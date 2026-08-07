from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from redis import Redis

from app.core.config import get_settings

settings = get_settings()
CONTENT_KEY = "dialog_spy:user_menu_content"
DEFAULT_OFFER_URL = "https://mooncloud.ltd/spy/terms.html#free"
VISIBLE_FIELDS = (
    "show_miniapp",
    "show_today",
    "show_stats",
    "show_subscription",
    "show_profile",
    "show_settings",
    "show_instruction",
    "show_offer",
)


def _enabled(data: dict[str, str], field: str) -> bool:
    return data.get(field, "1") not in {"0", "false", "False", "off"}


def _menu_config() -> dict[str, str]:
    redis = Redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=1)
    try:
        data: dict[str, str] = redis.hgetall(CONTENT_KEY)
        return {
            "offer_url": data.get("offer_url") or DEFAULT_OFFER_URL,
            **{field: "1" if _enabled(data, field) else "0" for field in VISIBLE_FIELDS},
        }
    except Exception:
        return {"offer_url": DEFAULT_OFFER_URL, **{field: "1" for field in VISIBLE_FIELDS}}
    finally:
        redis.close()


def enhanced_user_keyboard(admin: bool = False) -> InlineKeyboardMarkup:
    """Return the single configurable keyboard used by every user-facing screen."""
    config = _menu_config()
    rows: list[list[InlineKeyboardButton]] = []

    if config["show_miniapp"] == "1":
        rows.append([
            InlineKeyboardButton(
                text="📱 Открыть Mini App",
                web_app=WebAppInfo(url=settings.mini_app_url),
            )
        ])
    if config["show_today"] == "1":
        rows.append([InlineKeyboardButton(text="✨ Что сегодня", callback_data="user:today")])
    if config["show_stats"] == "1":
        rows.append([InlineKeyboardButton(text="📊 Статистика", callback_data="user:stats")])
    if config["show_subscription"] == "1":
        rows.append([InlineKeyboardButton(text="💎 Подписка", callback_data="user:subscription")])

    account_row: list[InlineKeyboardButton] = []
    if config["show_profile"] == "1":
        account_row.append(InlineKeyboardButton(text="👤 Профиль", callback_data="user:profile"))
    if config["show_settings"] == "1":
        account_row.append(InlineKeyboardButton(text="⚙️ Настройки", callback_data="user:settings"))
    if account_row:
        rows.append(account_row)

    if config["show_instruction"] == "1":
        rows.append([InlineKeyboardButton(text="📖 Инструкция", callback_data="help")])
    if config["show_offer"] == "1":
        rows.append([InlineKeyboardButton(text="📄 Оферта", url=config["offer_url"])])
    if admin:
        rows.append([InlineKeyboardButton(text="🛡 Админ-панель", callback_data="crm:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)