from telegram import Update
from telegram.ext import ContextTypes

async def _text_handler_impl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if not await check_and_rate_limit(update, context):
        return
    try:
        await _text_handler_inner(update, context)
    except Exception as e:
        _text = getattr(getattr(update, "message", None), "text", "") or ""
        _waiting = (getattr(context, "user_data", {}) or {}).get("waiting_for")
        logger.error(
            "text_handler error text=%r waiting_for=%r: %s",
            _text[:160], _waiting, e, exc_info=True,
        )
        try:
            await update.message.reply_text("⚠️ این بخش موقتاً در دسترس نیست. کمی بعد دوباره امتحان کنید.")
        except Exception as _exc:
            logger.debug("%s: %s", __name__, _exc)
