"""messages: ai responsibilities."""
from .messages_common import *  # noqa: F401,F403
from . import messages_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


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

async def _keep_typing(bot, chat_id, stop_event):
    """تا وقتی پاسخ آماده نشده، مدام حالت «در حال نوشتن...» را نشان بده."""
    import asyncio
    from telegram.constants import ChatAction
    while not stop_event.is_set():
        try:
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        except Exception as _exc:
            logger.debug("%s: %s", __name__, _exc)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=4)
        except Exception as _exc:
            logger.debug("%s: %s", __name__, _exc)

def _apply_voice_chat_flags(context, text: str) -> str | None:
    """
    فعال/غیرفعال کردن حالت مکالمه ویسی.
    پیام تأیید برای کاربر برمی‌گرداند یا None.
    """
    if wants_end_voice_chat(text):
        context.user_data["ai_voice_chat"] = False
        return "📝 حالت ویس خاموش شد. از این به بعد جواب‌ها بیشتر متنی است."
    if wants_voice_chat_mode(text):
        context.user_data["ai_voice_chat"] = True
        return (
            "🎙️ حالت مکالمه ویسی روشن شد.\n"
            "هر چی بگی (متن یا ویس) سعی می‌کنم با صدا جواب بدم.\n"
            "برای خاموش کردن بگو: «قطع ویس» یا «فقط متن»."
        )
    return None

async def _handle_special_ai_intents(update, context, user_id, text: str) -> bool:
    """نمودار، جستجو، یادآوری، موسیقی — True اگر کامل هندل شد."""
    import re
    from io import BytesIO
    from bot.database import add_reminder

    # HARD PRODUCT/PRICE GATE: product price requests must never fall through to
    # general AI knowledge. The shopping engine is the sole source for live
    # product prices, availability and seller links.
    try:
        from bot.handlers.special_ai_intents import (
            is_live_product_request,
            run_live_product_search,
        )
        if is_live_product_request(text):
            handled = await run_live_product_search(update, user_id, text)
            if handled:
                return True
    except Exception as _shopping_gate_exc:
        logger.exception("live product gate failed for user=%s: %s", user_id, _shopping_gate_exc)
        # Do NOT fall through to generic AI after a product-price request has
        # been positively identified. The helper itself returns a safe error.
        try:
            if is_live_product_request(text):
                await update.message.reply_text(
                    "⚠️ استعلام زنده قیمت محصول فعلاً در دسترس نیست؛ قیمت حدسی ارائه نمی‌کنم."
                )
                return True
        except Exception:
            pass

    # یادآوری
    rem = parse_natural_reminder(text)
    if rem:
        body, when, repeat_type, repeat_every = rem
        add_reminder(
            user_id,
            body,
            when.isoformat(),
            repeat_type=repeat_type,
            repeat_every=repeat_every,
        )
        repeat_label = {
            "daily": "روزانه",
            "weekly": "هفتگی",
            "monthly": "ماهانه",
            "every_minutes": f"هر {repeat_every} دقیقه",
            "every_hours": f"هر {repeat_every} ساعت",
        }.get(repeat_type, "یک‌بار")
        await update.message.reply_text(
            f"⏰ یادآوری ثبت شد.\nموضوع: {body}\nزمان: {when.strftime('%Y-%m-%d %H:%M')}\nتکرار: {repeat_label}",
        )
        return True
    # Weather/Crypto عمدی اینجا مستقیم پاسخ داده نمی‌شوند.
    # V41.1: اجازه بده Capability Router + Function Calling ابزار واقعی را اجرا کند
    # و خود AI نتیجه را به زبان طبیعی برای کاربر بنویسد؛ خروجی خام ابزار کپی نشود.
    # جستجوی وب
    m = re.match(r"^(جستجو|سرچ|search)\s*[:：]?\s*(.+)$", text, re.I | re.S)
    if m or re.search(r"\b(در\s*اینترنت|تو\s*وب)\s*جستجو", text, re.I):
        q = m.group(2).strip() if m else re.sub(r".*جستجو\s*[:：]?", "", text, flags=re.I).strip()
        notice = await update.message.reply_text("🔎 در حال جستجو...")
        try:
            result = await web_search(q)
            await update.message.reply_text(result)
        finally:
            try:
                await notice.delete()
            except Exception as _exc:
                logger.debug("%s: %s", __name__, _exc)
        return True
    # نمودار
    chart = parse_chart_request(text)
    if chart:
        title, labels, values, ctype = chart
        notice = await update.message.reply_text("📊 در حال رسم نمودار...")
        try:
            png = make_chart_image(title, labels, values, ctype)
            bio = BytesIO(png)
            bio.name = "chart.png"
            await update.message.reply_photo(photo=bio, caption=title)
        except Exception as e:
            await update.message.reply_text(f"⚠️ نمودار: {e}")
        finally:
            try:
                await notice.delete()
            except Exception as _exc:
                logger.debug("%s: %s", __name__, _exc)
        return True
    # موسیقی
    if re.search(r"(موسیقی|آهنگ|music)\s*بساز|(بساز|تولید)\s*(موسیقی|آهنگ|افکت)", text, re.I):
        notice = await update.message.reply_text("🎵 در حال ساخت موسیقی...")
        try:
            audio = await generate_music(text)
            bio = BytesIO(audio)
            bio.name = "music.mp3"
            await update.message.reply_audio(audio=bio, caption="🎵")
        except Exception as e:
            await update.message.reply_text(f"⚠️ ساخت موسیقی در دسترس نبود:\n{e}")
        finally:
            try:
                await notice.delete()
            except Exception as _exc:
                logger.debug("%s: %s", __name__, _exc)
        return True
    return False

def _split_telegram_text(text: str, limit: int = 3900) -> list[str]:
    """تقسیم متن بلند به چند پیام بدون قطع وسط کلمه در صورت امکان."""
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= limit:
        return [text]
    parts: list[str] = []
    rest = text
    while rest:
        if len(rest) <= limit:
            parts.append(rest)
            break
        cut = rest.rfind("\n", 0, limit)
        if cut < limit // 3:
            cut = rest.rfind(" ", 0, limit)
        if cut < limit // 3:
            cut = limit
        parts.append(rest[:cut].strip())
        rest = rest[cut:].strip()
    return [p for p in parts if p]

def _looks_truncated(answer: str) -> bool:
    """تشخیص تقریبی پاسخ ناقص (برای پیشنهاد دکمه ادامه)."""
    a = (answer or "").strip()
    if len(a) < 1200:
        return False
    # اگر خیلی بلند است یا با علائم ناتمام تمام شده
    if len(a) >= 2800:
        return True
    if a.endswith(("...", "…", ":", "—", "-", ",")):
        return True
    # جمله کامل تمام نشده
    if not re.search(r"[.!?؟۔]\s*$", a) and len(a) > 1600:
        return True
    return False

async def _reply_long_text(msg, text: str, *, prefix: str = "🤖 ", reply_markup=None):
    """ارسال پاسخ کامل؛ اگر بلند بود ادامه در پیام‌های بعدی. کیبورد فقط روی آخرین تکه."""
    body = (text or "").strip()
    chunks = _split_telegram_text(prefix + body, 3900)
    if not chunks:
        chunks = [prefix + "پاسخی دریافت نشد."]
    first = None
    total = len(chunks)
    for i, chunk in enumerate(chunks):
        is_last = i == total - 1
        kwargs = {}
        if is_last and reply_markup is not None:
            kwargs["reply_markup"] = reply_markup
        if i == 0:
            first = await msg.reply_text(chunk, **kwargs)
        else:
            body_chunk = chunk
            if body_chunk.startswith("🤖 "):
                body_chunk = body_chunk[2:].lstrip()
            await msg.reply_text(f"🤖 ادامه ({i+1}/{total})\n{body_chunk}", **kwargs)
    return first

async def _send_ai_answer(update, user_id, answer: str, *, prompt: str = "", stream: bool = True):
    """ارسال جواب AI کامل — بدون کلید مدل/حافظه؛ فقط در صورت نیاز دکمه ادامه."""
    msg = update.message
    aid = store_answer(user_id, answer, prompt=prompt)
    offer = _looks_truncated(answer) or len(answer or "") >= 1800
    # فقط دکمه ادامه؛ کلیدهای «انتخاب مدل» و «حذف حافظه» زیر پاسخ نباشد.
    kb = get_ai_result_keyboard(user_id, aid, offer_continue=offer)
    return await _reply_long_text(msg, answer, prefix="🤖 ", reply_markup=kb)

async def _ask_ai_stream_and_send(update, context, user_id: int, text: str):
    """استریم AI و ویرایش تدریجی پیام؛ در پایان همه تکه‌ها ارسال و دکمه ادامه اضافه می‌شود."""
    import asyncio
    from bot.services.ai_service import ask_ai_stream
    msg = update.message
    sent = await msg.reply_text("✍️ در حال نوشتن...")
    buf = []
    provider_label = ""
    try:
        last_edit = time.monotonic()
        last_len = 0
        last_rendered = "✍️ در حال نوشتن..."
        async for piece, label in ask_ai_stream(user_id, text):
            if label:
                provider_label = label
                continue
            if piece:
                buf.append(piece)
                current = "".join(buf)
                now = time.monotonic()
                if now - last_edit >= 0.8 and len(current) - last_len >= 80:
                    preview = "🤖 " + current
                    if len(preview) > 4000:
                        preview = preview[:3990] + "…"
                    if preview != last_rendered:
                        try:
                            await sent.edit_text(preview)
                            last_rendered = preview
                            last_edit, last_len = now, len(current)
                        except Exception as edit_error:
                            logger.debug("AI stream edit skipped: %s", edit_error)
                    else:
                        last_edit, last_len = now, len(current)
        answer = "".join(buf).strip()
        if not answer:
            raise RuntimeError("جواب خالی")
        aid = store_answer(user_id, answer, prompt=text)
        chunks = _split_telegram_text("🤖 " + answer, 3900)
        if not chunks:
            chunks = ["🤖 پاسخی دریافت نشد."]
        offer = _looks_truncated(answer) or len(answer) >= 1800
        # فقط دکمه ادامه؛ بدون کلید مدل/حافظه زیر پاسخ
        kb = get_ai_result_keyboard(user_id, aid, offer_continue=offer)

        # پیام اول: ویرایش همان «در حال نوشتن»
        first = chunks[0]
        total = len(chunks)
        edit_kwargs = {}
        if total == 1 and kb is not None:
            edit_kwargs["reply_markup"] = kb
        if first != last_rendered:
            try:
                await sent.edit_text(first, **edit_kwargs)
                last_rendered = first
            except Exception as edit_error:
                logger.warning("AI final edit failed; retrying same message: %s", edit_error)
                try:
                    await asyncio.sleep(0.15)
                    await sent.edit_text(first, **edit_kwargs)
                    last_rendered = first
                except Exception as retry_error:
                    logger.warning("AI final edit retry failed: %s", retry_error)
                    try:
                        await msg.reply_text(first, **edit_kwargs)
                    except Exception:
                        pass
        elif total == 1 and kb is not None:
            try:
                await sent.edit_text(first, reply_markup=kb)
            except Exception:
                pass

        # ادامه‌ها در پیام‌های بعدی تا هیچ بخشی حذف نشود
        for i, chunk in enumerate(chunks[1:], start=2):
            try:
                body = chunk
                if body.startswith("🤖 "):
                    body = body[2:].lstrip()
                kwargs = {}
                if i == total and kb is not None:
                    kwargs["reply_markup"] = kb
                await msg.reply_text(f"🤖 ادامه ({i}/{total})\n{body}", **kwargs)
            except Exception as cont_err:
                logger.warning("AI continuation send failed: %s", cont_err)
        return answer, provider_label or "ai"
    except Exception:
        try:
            await sent.delete()
        except Exception as _exc:
            logger.debug("%s: %s", __name__, _exc)
        raise

async def _send_ai_voice(update_or_msg, text: str, user_id: int, reply_markup=None):
    """ارسال ویس با پیام وضعیت «در حال ویس دادن»."""
    msg = getattr(update_or_msg, "message", None) or update_or_msg
    notice = await msg.reply_text("🔊 در حال ویس دادن...")
    try:
        audio = await text_to_speech(text)
        from io import BytesIO
        bio = BytesIO(audio)
        bio.name = "reply.mp3"
        kwargs = {"audio": bio, "caption": "🔊"}
        if reply_markup is not None:
            kwargs["reply_markup"] = reply_markup
        await msg.reply_audio(**kwargs)
    finally:
        try:
            await notice.delete()
        except Exception as _exc:
            logger.debug("%s: %s", __name__, _exc)

async def _ask_ai_with_typing(update, context, user_id, text):
    """AI request with stable chunked output and safe fallback semantics."""
    import asyncio
    stop_event = asyncio.Event()
    chat_id = update.effective_chat.id
    # فقط _ask_ai_stream_and_send یک پیام «✍️ در حال نوشتن...» می‌فرستد.
    # اینجا فقط ChatAction.TYPING برای وضعیت تایپ تلگرام فعال می‌شود تا
    # پیام وضعیت دوبار روی صفحه ایجاد نشود.
    from bot.utils.task_manager import spawn
    task = spawn(_keep_typing(context.bot, chat_id, stop_event), name=f"typing-{chat_id}")
    try:
        try:
            result = await _ask_ai_stream_and_send(update, context, user_id, text)
            context.user_data["_ai_already_sent"] = True
            return result
        except Exception as stream_error:
            logger.warning("AI chunked stream failed, using canonical fallback: %s", stream_error)
            context.user_data["_ai_already_sent"] = False
            return await ask_ai(user_id, text)
    finally:
        stop_event.set()
        try:
            await task
        except Exception as _exc:
            logger.debug("%s: %s", __name__, _exc)
