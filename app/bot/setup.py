from aiogram import Dispatcher, F
from aiogram.filters import Command

from app.core.config import get_settings
from app.services.telegram_bot import build_bot

settings = get_settings()
bot = build_bot(settings)
dispatcher = Dispatcher()

from app.bot.channel_gate_middleware import ChannelGateMiddleware  # noqa: E402
from app.bot.channel_check_override import router as channel_check_override_router  # noqa: E402
from app.bot.access_center import router as access_center_router  # noqa: E402
from app.bot.instruction_publisher import router as instruction_publisher_router  # noqa: E402
from app.bot.menu_editor_handlers import router as menu_editor_router  # noqa: E402
from app.bot.admin_menu_editor_patch import router as admin_menu_editor_router  # noqa: E402
from app.bot.profile_card_handlers import router as profile_card_router  # noqa: E402
from app.bot.statistics_card_v2_handlers import router as statistics_card_router  # noqa: E402
from app.bot.statistics_share_inline import router as statistics_share_inline_router  # noqa: E402
from app.bot.statistics_share_card import router as statistics_share_card_router, stats_keyboard  # noqa: E402
from app.bot.engagement_handlers import router as engagement_router  # noqa: E402
from app.bot.navigation_v019 import router as navigation_v019_router  # noqa: E402
from app.bot.health_handlers import router as health_router  # noqa: E402
from app.bot import product_experience_handlers as product_experience_module  # noqa: E402
from app.bot.product_experience_handlers import branded_send_access_screen, router as product_experience_router  # noqa: E402
from app.bot import user_experience_handlers as user_experience_module  # noqa: E402
from app.bot.user_experience_handlers import router as user_experience_router  # noqa: E402
from app.bot.archive_handlers import router as archive_router  # noqa: E402
from app.bot.group_archive_handlers import router as group_archive_router  # noqa: E402
from app.bot import access_funnel as access_funnel_module  # noqa: E402
from app.bot.access_funnel import router as access_funnel_router  # noqa: E402
from app.bot.impaya import cancel_command, pay_callback, pay_command  # noqa: E402
from app.bot.subscription import subscription_command  # noqa: E402
from app.bot import handlers as legacy_handlers, profile_card_handlers, user_handlers  # noqa: E402
from app.bot.enhanced_user_menu import enhanced_user_keyboard  # noqa: E402
from app.bot.instruction_store import instruction_content as synchronized_instruction_content  # noqa: E402
from app.bot.handlers import router as legacy_command_router  # noqa: E402
from app.bot.admin_handlers import router as legacy_admin_router  # noqa: E402


def _drop_named_handlers(observer, names: set[str]) -> None:
    observer.handlers[:] = [handler for handler in observer.handlers if getattr(handler.callback, "__name__", "") not in names]


_drop_named_handlers(legacy_command_router.message, {"start"})
legacy_command_router.callback_query.handlers.clear()
legacy_admin_router.callback_query.handlers.clear()
legacy_handlers.instruction_content = synchronized_instruction_content
user_experience_module.instruction_content = synchronized_instruction_content
access_funnel_module.send_access_screen = branded_send_access_screen
product_experience_module._stats_keyboard = stats_keyboard

dispatcher.message.outer_middleware(ChannelGateMiddleware())
dispatcher.callback_query.outer_middleware(ChannelGateMiddleware())
user_handlers.user_keyboard = enhanced_user_keyboard
profile_card_handlers._profile_keyboard = enhanced_user_keyboard

dispatcher.message.register(pay_command, Command("pay"))
dispatcher.message.register(cancel_command, Command("cancel"))
dispatcher.message.register(subscription_command, Command("subscription"))
dispatcher.callback_query.register(pay_callback, F.data == "impaya:pay")

dispatcher.include_router(channel_check_override_router)
dispatcher.include_router(access_center_router)
dispatcher.include_router(navigation_v019_router)
dispatcher.include_router(health_router)
dispatcher.include_router(instruction_publisher_router)
dispatcher.include_router(statistics_share_inline_router)
dispatcher.include_router(statistics_share_card_router)
dispatcher.include_router(engagement_router)
dispatcher.include_router(access_funnel_router)
dispatcher.include_router(group_archive_router)
dispatcher.include_router(menu_editor_router)
dispatcher.include_router(admin_menu_editor_router)
dispatcher.include_router(product_experience_router)
dispatcher.include_router(statistics_card_router)
dispatcher.include_router(profile_card_router)
dispatcher.include_router(user_experience_router)
dispatcher.include_router(archive_router)
