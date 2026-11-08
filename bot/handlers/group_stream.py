"""
استریم حرفه‌ای و لحظه‌ای برای پاسخ‌های AI — مخصوص گروه و پیوی.

ویژگی‌ها:
- نوشتن تدریجی با حس typewriter (ویرایش پیام با فاصله‌های کوتاه)
- هدر و فوتر تمیز در گروه‌ها
- مدیریت rate-limit تلگرام برای edit
- حالت loading جذاب
"""
from __future__ import annotations

import asyncio
import time
from typing import Optional, AsyncIterator, Tuple

from telegram import Update, Message, InlineKeyboardMarkup
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes

from bot.logger import logger
from bot.handlers.group_mode import (
    is_group_chat,
    group_ai_header,
    group_ai_footer,
    group_inline_actions,
    group_attribution,
    _esc,
)


# فاصله حداقل بین دو edit (تلگرام محدودیت دارد)
MIN_EDIT_INTERVAL = 0.55
# حداقل کاراکتر جدید برای هر ویرایش
MIN_CHARS_DELTA = 28
# حداکثر طول پیش‌نمایش استریم
MAX_STREAM_PREVIEW = 3800


LOADING_FRAMES = [
    "✍️ در حال نوشتن",
    "✍️ در حال نوشتن.",
    "✍️ در حال نوشتن..",
    "✍️ در حال نوشتن...",
]


def _cursor(frame_idx: int = 0) -> str:
    # نشانگر چشمک‌زن ساده
    return "▋" if (frame_idx % 2 == 0) else " "


async def keep_typing(bot, chat_id: int, stop_event: asyncio.Event, interval: float = 4.0):
    """نگه‌داشتن وضعیت «در حال تایپ» تا پایان تولید پاسخ."""
    while not stop_event.is_set():
        try:
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        except Exception:
            pass
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            continue


async def stream_ai_to_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    prompt: str,
    *,
    stream_fn=None,
) -> Optional[Message]:
    """
    پاسخ AI را به صورت لحظه‌ای روی یک پیام می‌نویسد (edit تدریجی).

    stream_fn باید یک async generator باشد که (piece, label) yield کند.
    """
    from bot.services.ai_service import ask_ai_stream
    from bot.services.ai_extras import store_answer, get_ai_result_keyboard

    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if not message or not chat:
        return None

    in_group = is_group_chat(chat)
    bot = context.bot

    # پیام اولیه
    if in_group:
        header = group_ai_header(user, streaming=True)
        initial = header + "✍️ <i>در حال فکر کردن...</i>"
        parse_mode = ParseMode.HTML
    else:
        initial = "✍️ در حال نوشتن..."
        parse_mode = None

    try:
        sent = await message.reply_text(initial, parse_mode=parse_mode)
    except Exception as exc:
        logger.warning("stream initial reply failed: %s", exc)
        return None

    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(keep_typing(bot, chat.id, stop_typing))

    buf: list[str] = []
    provider_label = ""
    last_edit = 0.0
    last_len = 0
    last_rendered = initial
    frame = 0
    final_answer = ""

    try:
        gen = stream_fn(user_id, prompt) if stream_fn else ask_ai_stream(user_id, prompt)
        async for piece, label in gen:
            if label:
                provider_label = label
                continue
            if not piece:
                continue
            buf.append(piece)
            current = "".join(buf)
            now = time.monotonic()
            delta = len(current) - last_len

            if now - last_edit >= MIN_EDIT_INTERVAL and delta >= MIN_CHARS_DELTA:
                preview_body = current
                if len(preview_body) > MAX_STREAM_PREVIEW:
                    preview_body = preview_body[: MAX_STREAM_PREVIEW - 10] + "…"

                if in_group:
                    header = group_ai_header(user, streaming=True)
                    preview = header + _esc(preview_body) + _cursor(frame)
                    pm = ParseMode.HTML
                else:
                    preview = "🤖 " + preview_body + _cursor(frame)
                    pm = None

                if preview != last_rendered:
                    try:
                        await sent.edit_text(preview, parse_mode=pm)
                        last_rendered = preview
                        last_edit = now
                        last_len = len(current)
                        frame += 1
                    except Exception as edit_err:
                        # پیام خیلی سریع یا محتوای یکسان
                        logger.debug("stream edit skip: %s", edit_err)

        final_answer = "".join(buf).strip()
        if not final_answer:
            final_answer = "متأسفم، پاسخ خالی برگشت. دوباره امتحان کن."

        # ذخیره برای ادامه
        aid = store_answer(user_id, final_answer, prompt=prompt)

        # ساخت پیام نهایی
        if in_group:
            header = group_ai_header(user, streaming=False)
            body = _esc(final_answer)
            footer = group_ai_footer()
            final_text = f"{header}{body}{footer}"
            if len(final_text) > 4090:
                final_text = final_text[:4080] + "…"
            kb = group_inline_actions(user_id, str(aid) if aid else None)
            try:
                await sent.edit_text(final_text, parse_mode=ParseMode.HTML, reply_markup=kb)
            except Exception:
                await sent.edit_text(final_answer[:4000], reply_markup=kb)
        else:
            # پیوی — همان سبک قبلی با بهبود
            offer = len(final_answer) >= 1600
            kb = get_ai_result_keyboard(user_id, aid, offer_continue=offer)
            text = "🤖 " + final_answer
            if len(text) > 4090:
                text = text[:4080] + "…"
            try:
                await sent.edit_text(text, reply_markup=kb)
            except Exception:
                await sent.reply_text(text[:4000], reply_markup=kb)

        return sent

    except Exception as exc:
        logger.warning("stream_ai_to_message failed: %s", exc)
        try:
            err = "⚠️ خطا در تولید پاسخ. چند لحظه بعد دوباره امتحان کن."
            await sent.edit_text(err)
        except Exception:
            pass
        return sent
    finally:
        stop_typing.set()
        try:
            await typing_task
        except Exception:
            pass
