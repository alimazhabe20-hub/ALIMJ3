"""Message text router.

The former monolithic _text_handler_inner is now an ordered dispatcher.
Each responsibility lives in a focused module; execution order is preserved.
"""
from .messages_common import *  # noqa: F401,F403
from . import messages_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})

from .messages_ai_router import handle_ai_text
from .messages_waiting_router import handle_pre_ai_waiting
from .messages_waiting_dispatch import handle_waiting_dispatch
from .messages_basic_menu import handle_basic_menu
from .messages_date_menu import handle_date_menu
from .messages_religious_menu import handle_religious_menu
from .messages_market_menu import handle_market_menu
from .messages_weather_menu import handle_weather_menu
from .messages_tools_menu import handle_tools_menu
from .messages_fun_menu import handle_fun_menu
from .messages_profile_menu import handle_profile_menu
from .messages_final_menu import handle_final_menu


def _is_back(text):
    t = text.strip()
    return t in ("🔙 بازگشت", "بازگشت") or "بازگشت" in t

def _is_back_more(text):
    return "بازگشت به بیشتر" in text

async def text_handler(*args, **kwargs):
    return await _legacy_text_handler(*args, **kwargs)

async def _text_handler_inner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name or "کاربر"
    city = get_user_city(user_id)

    # Keep the historical ordering exactly: downloader URL hook first.
    try:
        from bot.handlers.v71_handlers import handle_downloader_url_v71
        if await handle_downloader_url_v71(update, context, text):
            return
    except Exception as _dl_exc:
        logger.debug("downloader url hook: %s", _dl_exc)

    if await handle_pre_ai_waiting(update, context, text, user_id, city, first_name):
        return
    if await handle_ai_text(update, context, text, user_id, city, first_name, _is_back, _is_back_more):
        return
    if await handle_waiting_dispatch(update, context, text, user_id, city, first_name, _is_back, _is_back_more):
        return

    handlers = (
        handle_basic_menu, handle_date_menu, handle_religious_menu,
        handle_market_menu, handle_weather_menu, handle_tools_menu,
        handle_fun_menu, handle_profile_menu, handle_final_menu,
    )
    for handler in handlers:
        if await handler(update, context, text, user_id, city, first_name):
            return
