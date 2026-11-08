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

MIN_EDIT_INTERVAL = 0.45
MIN_CHARS_DELTA = 22
MAX_STREAM_PREVIEW = 3600

# فریم‌های انیمیشن لودینگ (چرخشی)
LOADING_FRAMES = [
    "⏳ ░░░░░░░░░░  در حال فکر…",
    "⏳ ▓░░░░░░░░░  در حال فکر…",
    "⏳ ▓▓░░░░░░░░  در حال فکر…",
    "⏳ ▓▓▓░░░░░░░  در حال فکر…",
    "⏳ ▓▓▓▓░░░░░░  در حال فکر…",
    "⏳ ▓▓▓▓▓░░░░░  در حال فکر…",
    "⏳ ▓▓▓▓▓▓░░░░  در حال فکر…",
    "⏳ ▓▓▓▓▓▓▓░░░  در حال فکر…",
    "⏳ ▓▓▓▓▓▓▓▓░░  در حال فکر…",
    "⏳ ▓▓▓▓▓▓▓▓▓░  در حال فکر…",
    "✍️ ▓▓▓▓▓▓▓▓▓▓  در حال نوشتن…",
]

WRITING_FRAMES = [
    "✍️ در حال نوشتن",
    "✍️ در حال نوشتن ·",
    "✍️ در حال نوشتن ··",
    "✍️ در حال نوشتن ···",
]


def _cursor(frame_idx: int = 0) -> str:
    return "▋" if (frame_idx % 2 == 0) else " "


GROUP_GROUNDED_SUFFIX = (
    "\n\n[قوانین سخت گروه]\n"
    "- فقط بر اساس واقعیت، داده زنده، یا دانش معتبر جواب بده.\n"
    "- اگر مطمئن نیستی، صریح بگو «نمی‌دانم» یا «اطلاعات کافی ندارم»؛ حدس نزن.\n"
    "- عدد، قیمت، تاریخ، آمار و اخبار را از خودت نساز.\n"
    "- جواب کوتاه، مفید و بدون حاشیه باشد (حداکثر چند پاراگراف کوتاه).\n"
    "- از تعریف الکی و جملات پرکننده پرهیز کن.\n"
    "- اگر سؤال مبهم است، یک سؤال کوتاه برای شفاف‌سازی بپرس.\n"
)


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


async def _animate_loading(sent: Message, header: str, stop_event: asyncio.Event, in_group: bool):
    """انیمیشن لودینگ تا وقتی استریم شروع شود."""
    i = 0
    while not stop_event.is_set():
        frame = LOADING_FRAMES[i % len(LOADING_FRAMES)]
        try:
            if in_group:
                text = header + f"<i>{frame}</i>"
                await sent.edit_text(text, parse_mode=ParseMode.HTML)
            else:
                await sent.edit_text(frame)
        except Exception:
            pass
        i += 1
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=0.55)
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

    # پرامپت هوشمند + کوتاه
    final_prompt = prompt
    if in_group:
        final_prompt = _build_group_prompt(prompt, short=short, max_chars=max_chars)

    if in_group:
        header = group_ai_header(user, streaming=True)
        initial = header + f"<i>{LOADING_FRAMES[0]}</i>"
        parse_mode = ParseMode.HTML
    else:
        initial = LOADING_FRAMES[0]
        parse_mode = None
        header = ""

    try:
        sent = await message.reply_text(initial, parse_mode=parse_mode)
    except Exception as exc:
        logger.warning("stream initial reply failed: %s", exc)
        return None

    stop_typing = asyncio.Event()
    stop_loading = asyncio.Event()
    typing_task = asyncio.create_task(keep_typing(bot, chat.id, stop_typing))
    loading_task = asyncio.create_task(_animate_loading(sent, header, stop_loading, in_group))

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
                stop_loading.set()
                try:
                    await loading_task
                except Exception:
                    pass
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
                    writing = WRITING_FRAMES[frame % len(WRITING_FRAMES)]
                    preview = f"{writing}\n\n🤖 " + preview_body + _cursor(frame)
                    pm = None

                if preview != last_rendered:
                    try:
                        await sent.edit_text(preview, parse_mode=pm)
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
            h = group_ai_header(user, streaming=False)
            body = _esc(final_answer)
            footer = group_ai_footer()
            final_text = f"{h}{body}{footer}"
            if len(final_text) > 4090:
                final_text = final_text[:4080] + "…"
            kb = group_inline_actions(user_id, str(aid) if aid else None)
            try:
                await sent.edit_text(final_text, parse_mode=ParseMode.HTML, reply_markup=kb)
            except Exception:
                await sent.edit_text(final_answer[:4000], reply_markup=kb)
        else:
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
            await sent.edit_text("⚠️ خطا در تولید پاسخ. چند لحظه بعد دوباره امتحان کن.")
        except Exception:
            pass
        return sent
    finally:
        stop_typing.set()
        stop_loading.set()
        for t in (typing_task, loading_task):
            try:
                await t
            except Exception:
                pass
