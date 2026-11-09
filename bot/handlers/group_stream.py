"""
استریم حرفه‌ای و لحظه‌ای برای پاسخ‌های AI — گروه و پیوی.

- انیمیشن لودینگ چندفریم
- پاسخ کوتاه‌تر خودکار در گروه
- پرامپت ضد توهم (grounded)
"""
from __future__ import annotations

import asyncio
import time
from typing import Optional

from telegram import Update, Message, InlineKeyboardMarkup
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes

from bot.logger import logger
from bot.handlers.group_mode import (
    is_group_chat,
    group_ai_header,
    group_ai_footer,
    group_inline_actions,
    _esc,
)

MIN_EDIT_INTERVAL = 0.35
MIN_CHARS_DELTA = 22
MAX_STREAM_PREVIEW = 3600


async def _safe_edit_or_reply(sent, text, *, parse_mode=None, reply_markup=None, fallback_message=None):
    """ویرایش امن؛ اگر پیام حذف شده بود، پیام جدید می‌فرستد."""
    try:
        kwargs = {}
        if parse_mode is not None:
            kwargs["parse_mode"] = parse_mode
        if reply_markup is not None:
            kwargs["reply_markup"] = reply_markup
        return await sent.edit_text(text, **kwargs)
    except Exception as exc:
        err = str(exc).lower()
        if "message to edit not found" in err or "message is not modified" in err or "not found" in err:
            try:
                chat_id = sent.chat_id
                bot = sent.get_bot() if hasattr(sent, "get_bot") else None
                if fallback_message is not None:
                    return await fallback_message.reply_text(
                        text, parse_mode=parse_mode, reply_markup=reply_markup
                    )
                if bot is not None:
                    return await bot.send_message(
                        chat_id=chat_id, text=text, parse_mode=parse_mode, reply_markup=reply_markup
                    )
            except Exception as exc2:
                logger.debug("safe_edit fallback failed: %s", exc2)
                return None
        logger.debug("safe_edit skip: %s", exc)
        return None




def _cursor(frame_idx: int = 0) -> str:
    return "▋" if (frame_idx % 2 == 0) else " "


GROUP_GROUNDED_SUFFIX = """

[قوانین پاسخ گروه]
- فقط به سؤال فعلی جواب بده؛ متن‌های قبلی را تکرار نکن.
- اگر داده زنده (قیمت/محصول) نداری، صادقانه بگو و حدس نزن.
- جواب کوتاه، مرتب و قابل‌استفاده باشد.
- لینک یا قیمت ساختگی نساز.
- از کپی کردن تاریخچه مکالمه در جواب خودداری کن.
"""

async def keep_typing(bot, chat_id: int, stop_event: asyncio.Event, interval: float = 3.5):
    while not stop_event.is_set():
        try:
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        except Exception:
            pass
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            continue



def _build_group_prompt(prompt: str, *, short: bool, max_chars: int) -> str:
    extra = GROUP_GROUNDED_SUFFIX
    if short:
        extra += (
            f"\n- سقف تقریبی پاسخ: حدود {max_chars} کاراکتر. "
            "مفصل‌گویی ممنوع مگر کاربر صریحاً بخواهد.\n"
        )
    return (prompt or "").strip() + extra


async def stream_ai_to_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    prompt: str,
    *,
    stream_fn=None,
) -> Optional[Message]:
    from bot.services.ai_service import ask_ai_stream
    from bot.services.ai_extras import store_answer, get_ai_result_keyboard

    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if not message or not chat:
        return None

    in_group = is_group_chat(chat)
    bot = context.bot

    short = False
    max_chars = 900
    if in_group:
        try:
            from bot.handlers.group_settings import is_group_ai_enabled, group_wants_short, group_max_chars
            if not is_group_ai_enabled(chat.id):
                try:
                    await message.reply_text(
                        "⏸ هوش مصنوعی در این گروه توسط ادمین خاموش شده.\n"
                        "ادمین می‌تواند با /groupsettings فعال کند."
                    )
                except Exception:
                    pass
                return None
            short = group_wants_short(chat.id)
            max_chars = group_max_chars(chat.id)
        except Exception as exc:
            logger.debug("group settings read: %s", exc)

    # پرامپت هوشمند + کوتاه + حافظه گروه
    final_prompt = prompt
    if in_group:
        try:
            from bot.handlers.group_parts.group_memory import get_context, add_turn
            from bot.handlers.group_mode import group_attribution
            reply = getattr(message, "reply_to_message", None)
            ctx = get_context(
                chat.id,
                user_id=user_id,
                reply_to_message_id=getattr(reply, "message_id", None),
            )
            speaker = group_attribution(user)
            base = (prompt or "").strip()
            if ctx:
                base = ("زمینهٔ مکالمه گروه:\n" + ctx[-6500:] +
                        f"\n\nپیام فعلی از طرف {speaker}:\n" + base)
            final_prompt = _build_group_prompt(base, short=short, max_chars=max_chars)
            add_turn(
                chat.id, "user", prompt, user_id=user_id, speaker=speaker,
                message_id=getattr(message, "message_id", None),
                reply_to_message_id=getattr(reply, "message_id", None),
            )
        except Exception:
            final_prompt = _build_group_prompt(prompt, short=short, max_chars=max_chars)

    # بدون انیمیشن لودینگ — فقط پیام شروع مینیمال برای استریم متن
    if in_group:
        header = group_ai_header(user, streaming=True)
        initial = header + "…"
        parse_mode = ParseMode.HTML
    else:
        header = ""
        initial = "…"
        parse_mode = None

    try:
        sent = await message.reply_text(initial, parse_mode=parse_mode)
    except Exception as exc:
        logger.warning("stream initial reply failed: %s", exc)
        return None

    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(keep_typing(bot, chat.id, stop_typing))

    buf: list[str] = []
    last_edit = 0.0
    last_len = 0
    last_rendered = initial
    frame = 0
    first_token = False

    try:
        gen = stream_fn(user_id, final_prompt) if stream_fn else ask_ai_stream(user_id, final_prompt)
        async for piece, label in gen:
            if label:
                continue
            if not piece:
                continue
            if not first_token:
                first_token = True
            buf.append(piece)
            current = "".join(buf)
            # در گروه پاسخ را زودتر کوتاه نگه می‌داریم در پیش‌نمایش
            if in_group and short and len(current) > max_chars + 200:
                current = current[: max_chars + 200]
            now = time.monotonic()
            delta = len(current) - last_len

            if now - last_edit >= MIN_EDIT_INTERVAL and delta >= MIN_CHARS_DELTA:
                preview_body = current
                if len(preview_body) > MAX_STREAM_PREVIEW:
                    preview_body = preview_body[: MAX_STREAM_PREVIEW - 10] + "…"

                if in_group:
                    h = group_ai_header(user, streaming=True)
                    preview = h + _esc(preview_body) + _cursor(frame)
                    pm = ParseMode.HTML
                else:
                    preview = "🤖 " + preview_body + _cursor(frame)
                    pm = None

                if preview != last_rendered:
                    try:
                        await _safe_edit_or_reply(sent, preview, parse_mode=pm, fallback_message=message)
                        last_rendered = preview
                        last_edit = now
                        last_len = len(current)
                        frame += 1
                    except Exception as edit_err:
                        logger.debug("stream edit skip: %s", edit_err)

        final_answer = "".join(buf).strip()
        if not final_answer:
            final_answer = "اطلاعات کافی برای پاسخ مطمئن ندارم. سؤال را دقیق‌تر بپرس."

        # کوتاه‌سازی نهایی در گروه
        if in_group and short and len(final_answer) > max_chars:
            cut = final_answer[:max_chars]
            # برش روی مرز جمله اگر ممکن باشد
            for sep in ("。", ".", "!", "?", "\n", "۔"):
                pos = cut.rfind(sep)
                if pos > max_chars * 0.55:
                    cut = cut[: pos + 1]
                    break
            final_answer = cut.rstrip() + "…"

        aid = store_answer(user_id, final_answer, prompt=prompt)
        if in_group:
            try:
                from bot.handlers.group_parts.group_memory import add_turn
                add_turn(chat.id, "bot", final_answer, speaker="روز زیبا", message_id=getattr(sent, "message_id", None))
                from bot.handlers.group_parts.metrics import mark
                mark("group_ai_reply")
            except Exception:
                pass

        if in_group:
            h = group_ai_header(user, streaming=False)
            body = _esc(final_answer)
            footer = group_ai_footer()
            final_text = f"{h}{body}{footer}"
            if len(final_text) > 4090:
                final_text = final_text[:4080] + "…"
            kb = group_inline_actions(user_id, str(aid) if aid else None)
            try:
                await _safe_edit_or_reply(sent, final_text, parse_mode=ParseMode.HTML, reply_markup=kb, fallback_message=message)
            except Exception:
                await _safe_edit_or_reply(sent, final_answer[:4000], reply_markup=kb, fallback_message=message)
        else:
            offer = len(final_answer) >= 1600
            kb = get_ai_result_keyboard(user_id, aid, offer_continue=offer)
            text = "🤖 " + final_answer
            if len(text) > 4090:
                text = text[:4080] + "…"
            try:
                await _safe_edit_or_reply(sent, text, reply_markup=kb, fallback_message=message)
            except Exception:
                await sent.reply_text(text[:4000], reply_markup=kb)

        return sent

    except Exception as exc:
        logger.warning("stream_ai_to_message failed: %s", exc)
        try:
            await _safe_edit_or_reply(
                sent,
                "⚠️ خطا در تولید پاسخ. چند لحظه بعد دوباره امتحان کن.",
                fallback_message=message,
            )
        except Exception:
            try:
                await message.reply_text("⚠️ خطا در تولید پاسخ. چند لحظه بعد دوباره امتحان کن.")
            except Exception:
                pass
        return sent
    finally:
        stop_typing.set()
        for t in (typing_task,):
            try:
                await t
            except Exception:
                pass
