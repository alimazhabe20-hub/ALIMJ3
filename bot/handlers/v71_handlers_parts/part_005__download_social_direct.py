from telegram import Update
from telegram.ext import ContextTypes

# Auto-split part 5: _download_social_direct
async def _download_social_direct(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str) -> None:
    """Mirror insta-downloader-bot handle_link: download then reply_video/document."""
    from bot.services.insta_downloader import download as insta_download, is_video_path, cleanup_path
    from bot.services.downloader import MAX_BYTES, user_message

    notice = await update.message.reply_text("⏳ در حال دانلود...")
    path = None
    try:
        path = await insta_download(url)
        size = 0
        try:
            from pathlib import Path as _P
            size = _P(path).stat().st_size
        except Exception:
            size = 0
        if size > MAX_BYTES:
            await notice.edit_text(user_message("too_large"))
            return

        try:
            await notice.edit_text("📤 در حال ارسال...")
        except Exception as exc:
            logger.debug("non-fatal exception: %s", exc)

        from bot.services.telegram_upload import send_media
        await send_media(update.message, path, title=__import__("pathlib").Path(path).name)
        try:
            await notice.delete()
        except Exception as exc:
            logger.debug("non-fatal exception: %s", exc)
    except Exception as exc:
        logger.exception("social direct download failed: %s", exc)
        err = str(exc)
        if err in {"telegram_standard_api_limit", "telegram_upload_too_large"}:
            from bot.services.telegram_upload import upload_error_message
            try:
                await notice.edit_text(upload_error_message(err))
            except Exception:
                await update.message.reply_text(upload_error_message(err))
            return
        low = err.lower()
        if "gallery-dl" in low and ("نصب" in err or "not found" in low or "no such file" in low):
            code = "gallery_dl_missing"
        elif any(x in low for x in ("login", "captcha", "403", "401", "private", "cookie")):
            code = "site_blocked"
        elif "too large" in low or "max-filesize" in low:
            code = "too_large"
        else:
            code = "failed"
        try:
            await notice.edit_text(user_message(code))
        except Exception:
            await update.message.reply_text(user_message(code))
    finally:
        cleanup_path(path)
