"""
پاسخ مستقیم گروه — مسیر ساده و مقاوم.
اگر fast-path یا AI موفق نشد، باز هم یک پیام خطا می‌فرستد تا سکوت کامل رخ ندهد.
"""
from __future__ import annotations

import re
from telegram import Update
from telegram.ext import ContextTypes

from bot.logger import logger
from bot.handlers.group_mode import (
    is_group_chat,
    should_respond_in_group,
    clean_group_prompt,
    get_bot_username,
)


async def try_group_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> bool:
    """
    Returns True if this update was handled as a group reply attempt.
    """
    chat = update.effective_chat
    message = update.effective_message
    user = update.effective_user
    if not chat or not message or not user or not is_group_chat(chat):
        return False

    ok, reason = should_respond_in_group(update, context)
    logger.info("group_reply gate chat=%s ok=%s reason=%s text=%r", chat.id, ok, reason, (text or "")[:100])
    if not ok:
        # اجبار برای کلیدواژه‌های واضح حتی اگر gate رد کند
        t = (text or "").strip()
        force_keys = ("قیمت", "دلار", "طلا", "هوا", "ربات", "بیتکوین", "بیت‌کوین", "/ask", "/ai", "http://", "https://", "tiktok", "instagram", "youtube", "دانلود", "تحلیل", "اینو", "اینا", "عکس", "تصویر")
        if not any(k in t for k in force_keys):
            return False
        logger.info("group_reply force-override for clear keyword")

    bot_uname = get_bot_username(context)
    prompt = clean_group_prompt(text, bot_uname) or (text or "").strip()
    if not prompt:
        try:
            await message.reply_text(
                "👋 من اینجام.\nبپرس مثلاً: قیمت دلار · هوای قم · /ask سؤال"
            )
        except Exception as exc:
            logger.warning("group empty prompt reply failed: %s", exc)
        return True


    # 0b) تحلیل عکس/ویدیو وقتی به مدیا ریپلای شده
    try:
        reply = message.reply_to_message
        wants_vision = bool(re.search(r"تحلیل|اینو|اینا|ببین|چیه|چی میبینی|توضیح|describe|analyze", prompt, re.I))
        if reply and (wants_vision or "ربات" in (text or "")):
            photo = None
            video = None
            if reply.photo:
                photo = reply.photo[-1]
            elif reply.document and (reply.document.mime_type or "").startswith("image/"):
                photo = reply.document
            elif reply.video or reply.video_note:
                video = reply.video or reply.video_note
            if photo or video:
                logger.info("group_reply vision analyze reply media")
                notice = await message.reply_text("🔎 در حال تحلیل تصویر...")
                try:
                    if photo:
                        tg_file = await photo.get_file()
                        data = bytes(await tg_file.download_as_bytearray())
                        from bot.services.ai_service import ask_ai_media
                        result = await ask_ai_media(
                            user.id,
                            prompt or "این تصویر را کوتاه و دقیق تحلیل کن.",
                            images=[(data, "image/jpeg")],
                        )
                        if isinstance(result, tuple):
                            result = result[0]
                        await message.reply_text(f"🤖 {str(result)[:4000]}")
                    else:
                        tg_file = await video.get_file()
                        data = bytes(await tg_file.download_as_bytearray())
                        from bot.services.ai_service import analyze_video
                        mime = getattr(video, "mime_type", None) or "video/mp4"
                        result = await analyze_video(data, prompt or "این ویدیو را کوتاه تحلیل کن.", mime=mime)
                        await message.reply_text(f"🤖 {str(result)[:4000]}")
                except Exception as exc:
                    logger.warning("group vision failed: %s", exc)
                    try:
                        await message.reply_text("⚠️ تحلیل تصویر/ویدیو الان ممکن نشد. دوباره امتحان کن.")
                    except Exception:
                        pass
                finally:
                    try:
                        await notice.delete()
                    except Exception:
                        pass
                return True
    except Exception as exc:
        logger.warning("group_reply vision branch error: %s", exc)

    # 0) دانلودر واقعی برای لینک‌های سوشال/ویدیو
    try:
        import re
        has_url = bool(re.search(r"https?://|www\.", prompt, re.I))
        social = bool(re.search(
            r"(instagram|tiktok|facebook|twitter|x\.com|youtube|youtu\.be|vimeo|dailymotion)",
            prompt,
            re.I,
        ))
        if has_url and social:
            logger.info("group_reply downloader url=%r", prompt[:140])
            handled = False
            try:
                from bot.handlers.v70_handlers import handle_downloader_url
                handled = await handle_downloader_url(update, context, prompt)
            except Exception as exc:
                logger.warning("group v70 downloader failed: %s", exc)
            if handled:
                return True
            try:
                from bot.services.downloader import extract_url
                from bot.services.insta_downloader import is_social_url
                from bot.handlers.v71_handlers import _download_social_direct
                url = extract_url(prompt) or prompt.strip()
                if url and is_social_url(url):
                    await _download_social_direct(update, context, url)
                    return True
            except Exception as exc:
                logger.warning("group v71 social download failed: %s", exc)
            try:
                await message.reply_text(
                    "⚠️ دانلود این لینک الان ممکن نشد. دوباره بفرست یا در پیوی امتحان کن."
                )
            except Exception:
                pass
            return True
    except Exception as exc:
        logger.warning("group_reply download branch error: %s", exc)

    # 1) Fast-path
    try:
        from bot.handlers.group_settings import group_fast_path_enabled, is_group_ai_enabled
        if not is_group_ai_enabled(chat.id):
            await message.reply_text("⏸ AI این گروه خاموش است. ادمین: /groupsettings")
            return True
        if group_fast_path_enabled(chat.id):
            from bot.handlers.group_parts.fast_path import run_fast_path
            fp = await run_fast_path(prompt)
            logger.info("group_reply fast_path result=%s", "HIT" if fp else "MISS")
            if fp:
                try:
                    await message.reply_text(fp, parse_mode="HTML", disable_web_page_preview=True)
                except Exception:
                    await message.reply_text(str(fp)[:4000])
                return True
    except Exception as exc:
        logger.warning("group_reply fast_path error: %s", exc)

    # 2) AI stream
    try:
        from bot.handlers.group_stream import stream_ai_to_message
        sent = await stream_ai_to_message(update, context, user.id, prompt)
        if sent is not None:
            return True
        logger.warning("group_reply stream returned None")
    except Exception as exc:
        logger.warning("group_reply stream error: %s", exc)

    # 3) Fallback AI non-stream
    try:
        from bot.services.ai_service import ask_ai
        answer = await ask_ai(user.id, prompt)
        if isinstance(answer, tuple):
            answer = answer[0]
        if answer:
            await message.reply_text(f"🤖 {str(answer)[:4000]}")
            return True
    except Exception as exc:
        logger.warning("group_reply ask_ai error: %s", exc)

    # 4) Never silent
    try:
        await message.reply_text(
            "⚠️ الان نتونستم جواب بدم. چند ثانیه بعد دوباره بپرس.\n"
            "یا بنویس: /ask قیمت دلار"
        )
    except Exception as exc:
        logger.warning("group_reply final fallback failed: %s", exc)
    return True
