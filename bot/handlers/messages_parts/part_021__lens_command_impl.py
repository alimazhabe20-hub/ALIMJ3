from telegram import Update
from telegram.ext import ContextTypes

async def _lens_command_impl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اجرای Lens محلی روی عکسی که کاربر به آن Reply کرده است."""
    if not update.message:
        return
    reply = update.message.reply_to_message
    if not reply:
        await update.message.reply_text("📷 روی یک عکس Reply کن و بعد /lens را بفرست.")
        return
    photo = reply.photo[-1] if reply.photo else None
    if not photo and reply.document:
        mime = reply.document.mime_type or ""
        if mime.startswith("image/"):
            photo = reply.document
    if not photo:
        await update.message.reply_text("❌ پیام Reply شده یک تصویر نیست.")
        return
    notice = await update.message.reply_text("🔎 در حال تحلیل تصویر...")
    try:
        tg_file = await photo.get_file()
        data = bytes(await tg_file.download_as_bytearray())
        result = await visual_search(data, caption="lens")
        await update.message.reply_text(result[:4000])
    except Exception as exc:
        logger.error("image analysis failed: %s", exc, exc_info=True)
        await update.message.reply_text("⚠️ تحلیل تصویر فعلاً در دسترس نیست. چند ثانیه بعد دوباره امتحان کنید.")
    finally:
        try:
            await notice.delete()
        except Exception as _exc:
            logger.debug("%s: %s", __name__, _exc)
