"""Unified group entry point for captioned photos/videos and image documents."""
from __future__ import annotations

import re

from telegram import Update
from telegram.ext import ContextTypes

from bot.logger import logger
from bot.handlers.group_mode import is_group_chat, should_respond_in_group, get_bot_username, clean_group_prompt
from bot.handlers.group_guard import claim_group_update, group_ai_access_allowed, safe_group_reply

_MEDIA_INTENT = re.compile(
    r"تحلیل|بررسی|توضیح|توصیف|ببین|اینو|اینا|این عکس|این ویدیو|چیه|چی میبینی|متن.?خوانی|ocr|analy[sz]e|describe|what is",
    re.I,
)


async def group_media_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if not msg or not chat or not user or not is_group_chat(chat):
        return False

    caption = (msg.caption or "").strip()
    if not caption:
        return False
    ok, reason = should_respond_in_group(update, context)
    if not ok:
        return False
    if not await group_ai_access_allowed(update, context, notify=True):
        return True
    if not claim_group_update(update, context, namespace="media"):
        logger.info("duplicate group media ignored chat=%s message=%s", chat.id, msg.message_id)
        return True

    prompt = clean_group_prompt(caption, get_bot_username(context)) or caption
    if not _MEDIA_INTENT.search(prompt):
        return False

    notice = await safe_group_reply(msg, "🔎 در حال بررسی رسانه...")
    try:
        if msg.photo:
            photo = msg.photo[-1]
            tg_file = await photo.get_file()
            data = bytes(await tg_file.download_as_bytearray())
            mime = "image/jpeg"
            from bot.services.ai_service import ask_ai_media
            result = await ask_ai_media(
                user.id,
                prompt or "این تصویر را دقیق توصیف و تحلیل کن.",
                images=[(data, mime)],
            )
            if isinstance(result, tuple):
                result = result[0]
        elif msg.document:
            doc = msg.document
            mime = (doc.mime_type or "").lower()
            filename = (doc.file_name or "").lower()
            if not (mime.startswith("image/") or filename.endswith((".jpg", ".jpeg", ".png", ".webp"))):
                return False
            if doc.file_size and doc.file_size > 10 * 1024 * 1024:
                await safe_group_reply(msg, "❌ حجم تصویر بیشتر از ۱۰ مگابایت است.")
                return True
            tg_file = await doc.get_file()
            data = bytes(await tg_file.download_as_bytearray())
            from bot.services.ai_service import ask_ai_media
            result = await ask_ai_media(user.id, prompt, images=[(data, mime or "image/jpeg")])
            if isinstance(result, tuple):
                result = result[0]
        elif msg.video or msg.video_note:
            video = msg.video or msg.video_note
            if video.file_size and video.file_size > 20 * 1024 * 1024:
                await safe_group_reply(msg, "❌ حجم ویدیو بیشتر از ۲۰ مگابایت است؛ یک ویدیوی کوتاه‌تر بفرست.")
                return True
            tg_file = await video.get_file()
            data = bytes(await tg_file.download_as_bytearray())
            from bot.services.ai_service import analyze_video
            result = await analyze_video(data, prompt, mime=getattr(video, "mime_type", None) or "video/mp4")
        else:
            return False

        answer = str(result or "تحلیل قابل اتکایی از این رسانه به دست نیامد.").strip()
        await safe_group_reply(msg, "🤖 " + answer[:3900], disable_web_page_preview=True)
    except Exception as exc:
        logger.warning("group media analysis failed chat=%s: %s", chat.id, exc, exc_info=True)
        await safe_group_reply(msg, "⚠️ تحلیل رسانه انجام نشد. لطفاً کمی بعد دوباره تلاش کن.")
    finally:
        if notice:
            try:
                await notice.delete()
            except Exception:
                pass
    return True
