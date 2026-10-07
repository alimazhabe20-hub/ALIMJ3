async def _safe_reply(update, text, **kwargs):
    """ارسال امن بدون کرش بابت Markdown"""
    kwargs.pop("parse_mode", None)
    try:
        await update.message.reply_text(text, **kwargs)
    except Exception:
        try:
            await update.message.reply_text(str(text)[:4000], reply_markup=kwargs.get("reply_markup"))
        except Exception as _exc:
            logger.debug("%s: %s", __name__, _exc)
