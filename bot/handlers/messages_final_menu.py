"""Semantic message-routing handlers. Extracted from the legacy text handler without removing behavior."""
from .messages_common import *  # noqa: F401,F403
from . import messages_common as _common
from .messages_main import _send_main
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})

async def handle_final_menu(update, context, text, user_id, city=None, first_name=None):
    if text.startswith("فارسی") or text == "فارسی 🇮🇷":
        update_user_field(user_id, "language", "fa"); await _send_main(update, context, await build_message(user_id, first_name, city), user_id); return
    if text.startswith("English") or text == "English 🇬🇧":
        update_user_field(user_id, "language", "en"); await _send_main(update, context, await build_message(user_id, first_name, city), user_id); return
    if "العربية" in text or "العربيه" in text:
        update_user_field(user_id, "language", "ar"); await _send_main(update, context, await build_message(user_id, first_name, city), user_id); return
    if text in ALL_CITIES:
        update_user_field(user_id, "city", text); update_user_field(user_id, "country", CITY_COUNTRY.get(text, "Iran"))
        await _send_main(update, context, f"✅ شهر → **{text}**\n\n" + await build_message(user_id, first_name, text), user_id); return
    return False
