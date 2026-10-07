"""Semantic message-routing handlers. Extracted from the legacy text handler without removing behavior."""
from .messages_common import *  # noqa: F401,F403
from . import messages_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})

async def handle_tools_menu(update, context, text, user_id, city=None, first_name=None):
    # ابزار
    if text in ("🔢 ماشین‌حساب", "ماشین‌حساب"):
        context.user_data["waiting_for"] = "calc"; track_usage(user_id, "calc")
        await update.message.reply_text("🔢 `2+3*4`", reply_markup=get_tools_keyboard()); return
    if text in ("🔐 پسورد تصادفی", "پسورد تصادفی"):
        track_usage(user_id, "password")
        pwd = generate_password(16)
        await update.message.reply_text(
            "🔐 پسورد تصادفی:\n\n<code>" + pwd + "</code>\n\n👆 روی پسورد بزنید تا کپی شود",
            reply_markup=get_tools_keyboard(),
            parse_mode="HTML",
        ); return
    if text in ("📝 شمارش متن", "شمارش متن"):
        context.user_data["waiting_for"] = "count_text"; track_usage(user_id, "count")
        await update.message.reply_text("📝 متن را بفرستید:", reply_markup=get_tools_keyboard()); return
    return False
