"""Callback action: ai_memory (حذف حافظه).

مقاوم‌سازی‌شده:
- import صریح (بدون وابستگی به globals از callbacks_core)
- try/except کامل تا به error_handler عمومی نرسد
- پاک کردن حافظه کوتاه‌مدت + بلندمدت با دکمه «حذف حافظه»
"""
from __future__ import annotations

from bot.logger import logger


async def handle(update, context):
    query = update.callback_query
    data = getattr(query, "data", None) or ""
    user = update.effective_user
    user_id = int(user.id) if user else 0

    if data != "ai_clear_memory":
        return

    # اول callback را جواب بده تا تلگرام timeout ندهد
    try:
        await query.answer("حافظه AI پاک شد ✅", show_alert=False)
    except Exception as exc:
        logger.debug("ai_clear_memory answer failed: %s", exc)

    # پاک‌سازی حافظه
    try:
        from bot.services.ai_service import clear_history

        # دکمه «حذف حافظه» باید هم تاریخچه گفتگو و هم حافظه بلندمدت را پاک کند
        clear_history(user_id, clear_long_term=True)
    except Exception as exc:
        logger.exception("ai_clear_memory clear_history failed user=%s: %s", user_id, exc)
        try:
            # fallback مستقیم دیتابیس
            from bot.database import clear_ai_history_summary, delete_ai_memory

            clear_ai_history_summary(user_id)
            delete_ai_memory(user_id)
        except Exception as exc2:
            logger.exception("ai_clear_memory db fallback failed: %s", exc2)

    # به‌روزرسانی کیبورد همان پیام (اگر ممکن باشد)
    try:
        from bot.utils.helpers import get_ai_keyboard

        await query.edit_message_reply_markup(reply_markup=get_ai_keyboard(user_id))
    except Exception as exc:
        logger.debug("ai_clear_memory edit markup failed: %s", exc)

    # پیام تأیید
    text = (
        "✅ حافظه AI پاک شد.\n"
        "• تاریخچه گفت‌وگوی فعلی\n"
        "• خلاصه گفتگوهای قبلی\n"
        "• حافظه بلندمدت\n\n"
        "از این به بعد بدون حافظه قبلی ادامه می‌دهم."
    )
    try:
        if query.message is not None:
            await query.message.reply_text(text)
        elif update.effective_chat is not None:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=text)
    except Exception as exc:
        logger.debug("ai_clear_memory confirm message failed: %s", exc)
