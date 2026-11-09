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
        force_keys = ("قیمت", "دلار", "طلا", "هوا", "ربات", "بیتکوین", "بیت‌کوین", "/ask", "/ai")
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
