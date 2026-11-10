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
        return False

    # Enforce admin-only mode against Telegram's actual group membership.
    try:
        from bot.handlers.group_settings import group_admin_only
        if group_admin_only(chat.id):
            from bot.handlers.group_mode import user_is_group_admin
            if not await user_is_group_admin(update, context):
                return False
    except Exception as exc:
        logger.warning("group admin gate failed closed: %s", exc)
        return False

    bot_uname = get_bot_username(context)
    prompt = clean_group_prompt(text, bot_uname) or (text or "").strip()

    # Intent هوشمند
    try:
        from bot.handlers.group_parts.intent import detect_intent
        intent, intent_q = detect_intent(prompt or text)
        logger.info("group_reply intent=%s q=%r", intent, (intent_q or "")[:80])
    except Exception:
        intent, intent_q = "ai", prompt

    if intent == "help" or not (prompt or "").strip() or (prompt or "").strip() in {"ربات", "هوشمند", "!", "bot"}:
        try:
            from bot.handlers.group_parts.group_ui import group_help_text
            await message.reply_text(group_help_text(), parse_mode="HTML", disable_web_page_preview=True)
        except Exception as exc:
            logger.warning("group help failed: %s", exc)
            await message.reply_text("👋 من اینجام. مثال: قیمت دلار · هوای قم · /ask سؤال")
        return True

    # Explicit group conversation summary command.
    if re.search(r"(?:خلاصه|جمع.?بندی).{0,18}(?:مکالمه|گفتگو|گروه)|(?:مکالمه|گفتگو).{0,18}(?:خلاصه|جمع.?بندی)", prompt, re.I):
        try:
            from bot.handlers.group_parts.group_memory import summarize_group
            notice = await message.reply_text("🧠 در حال خلاصه‌سازی مکالمات گروه...")
            try:
                summary = await summarize_group(chat.id, user.id)
                await message.reply_text("📚 خلاصهٔ مکالمه گروه:\n" + str(summary)[:3800])
            finally:
                try:
                    await notice.delete()
                except Exception:
                    pass
        except Exception as exc:
            logger.warning("group conversation summary failed: %s", exc)
            await message.reply_text("⚠️ خلاصه‌سازی مکالمه فعلاً ممکن نشد.")
        return True

    # A text request may refer to an image, video, document or audio in the replied message.
    reply_media = message.reply_to_message
    if reply_media and any(getattr(reply_media, name, None) for name in ("photo", "video", "video_note", "document", "voice", "audio", "sticker")):
        try:
            from bot.handlers.group_parts.group_media import handle_group_media
            if await handle_group_media(update, context, source_message=reply_media, prompt=prompt):
                return True
        except Exception as exc:
            logger.warning("group reply media pipeline failed: %s", exc)
    if not prompt or prompt in {"ربات", "هوشمند", "!", "bot"}:
        try:
            await message.reply_text(
                "👋 من اینجام.\nمثال‌ها:\n• قیمت دلار\n• هوای قم\n• ربات باتری ایفون ۶ پلاس پیدا کن\n• روی عکس Reply کن: ربات اینو تحلیل کن\n• /ask سؤال آزاد"
            )
        except Exception as exc:
            logger.warning("group empty prompt reply failed: %s", exc)
        return True


    # 0b) تحلیل عکس/ویدیو — ریپلای به مدیا یا کپشن
    try:
        reply = message.reply_to_message
        # تحلیل بازار (طلا/کریپتو) vision نیست
        _p = prompt or text or ""
        if re.search(r"تحلیل\s*(?:طلا|بیتکوین|بیت‌کوین|اتریوم|کریپتو|btc|eth|بازار)", _p, re.I):
            wants_vision = False
        else:
            wants_vision = bool(
                re.search(
                    r"این\s*عکس|این\s*تصویر|عکس\s*رو|تحلیل\s*عکس|اینو\s*تحلیل|اینا\s*تحلیل|describe|analyze\s*(?:this\s*)?(?:image|photo)",
                    _p,
                    re.I,
                )
            )

        async def _extract_image_bytes(msg):
            if not msg:
                return None
            # photo sizes
            if getattr(msg, "photo", None):
                p = msg.photo[-1]
                f = await p.get_file()
                return bytes(await f.download_as_bytearray()), "image/jpeg"
            # document image
            doc = getattr(msg, "document", None)
            if doc:
                mime = (doc.mime_type or "").lower()
                name = (doc.file_name or "").lower()
                if mime.startswith("image/") or name.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
                    f = await doc.get_file()
                    return bytes(await f.download_as_bytearray()), (mime or "image/jpeg")
            # sticker as static if available
            st = getattr(msg, "sticker", None)
            if st and not getattr(st, "is_animated", False) and not getattr(st, "is_video", False):
                try:
                    f = await st.get_file()
                    return bytes(await f.download_as_bytearray()), "image/webp"
                except Exception:
                    return None
            return None

        async def _extract_video_bytes(msg):
            if not msg:
                return None, None
            v = getattr(msg, "video", None) or getattr(msg, "video_note", None)
            if not v:
                return None, None
            f = await v.get_file()
            data = bytes(await f.download_as_bytearray())
            mime = getattr(v, "mime_type", None) or "video/mp4"
            return data, mime

        img = None
        # 1) ریپلای به مدیا
        if reply and (wants_vision or "ربات" in (text or "")):
            img = await _extract_image_bytes(reply)
            if img is None:
                vdata, vmime = await _extract_video_bytes(reply)
                if vdata:
                    logger.info("group_reply vision: video from reply")
                    notice = await message.reply_text("🔎 در حال تحلیل ویدیو...")
                    try:
                        from bot.services.ai_service import analyze_video
                        result = await analyze_video(
                            vdata,
                            prompt or "این ویدیو را کوتاه و دقیق تحلیل کن.",
                            mime=vmime,
                        )
                        await message.reply_text(f"🤖 {str(result)[:4000]}")
                    except Exception as exc:
                        logger.warning("group video analyze failed: %s", exc)
                        await message.reply_text("⚠️ تحلیل ویدیو ممکن نشد.")
                    finally:
                        try:
                            await notice.delete()
                        except Exception:
                            pass
                    return True
            else:
                logger.info("group_reply vision: image from reply (%s bytes)", len(img[0]))

        # 2) اگر خود پیام عکس+کپشن باشد (نباید اینجا باشد چون text_handler است)
        if img is None and wants_vision:
            logger.info(
                "group_reply vision: no media on reply. reply=%s photo=%s doc=%s",
                bool(reply),
                bool(getattr(reply, "photo", None)) if reply else None,
                bool(getattr(reply, "document", None)) if reply else None,
            )
            if wants_vision:
                await message.reply_text(
                    "📷 عکس را مستقیم بفرست با کپشن «ربات تحلیل کن» یا Forward کن."
                )
                return True

        if img is not None:
            data, mime = img
            notice = await message.reply_text("🔎 در حال تحلیل تصویر...")
            try:
                result = None
                try:
                    from bot.services.ai_service import ask_ai_media
                    result = await ask_ai_media(
                        user.id,
                        prompt or "این تصویر را کامل و دقیق تحلیل کن. محتوا، متن داخل عکس، اشیاء و نکات مهم را بگو.",
                        images=[(data, mime)],
                    )
                    if isinstance(result, tuple):
                        result = result[0]
                except Exception as exc1:
                    logger.warning("ask_ai_media failed: %s", exc1)
                    try:
                        from bot.services.visual_search import visual_search
                        result = await visual_search(data, caption=prompt or "lens")
                    except Exception as exc2:
                        logger.warning("visual_search failed: %s", exc2)
                        result = None
                if result:
                    await message.reply_text(f"🤖 {str(result)[:4000]}")
                else:
                    await message.reply_text("⚠️ تحلیل تصویر انجام نشد. مدل بینایی در دسترس نبود.")
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
