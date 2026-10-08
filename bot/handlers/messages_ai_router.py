"""Semantic message-routing handlers. Extracted from the legacy text handler without removing behavior."""
from .messages_common import *  # noqa: F401,F403
from . import messages_common as _common
from .messages_ai import (
    _apply_voice_chat_flags, _ask_ai_with_typing, _handle_special_ai_intents,
    _send_ai_answer, _send_ai_voice,
)
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})

def _is_back(text):
    t = text.strip()
    return t in ("🔙 بازگشت", "بازگشت") or "بازگشت" in t

def _is_back_more(text):
    return "بازگشت به بیشتر" in text

async def handle_ai_text(update, context, text, user_id, city=None, first_name=None):
    if context.user_data.get("ai_mode"):
        if _is_back(text) or _is_back_more(text):
            context.user_data.pop("ai_mode", None)
            context.user_data.pop("waiting_for", None)
            await update.message.reply_text("➕ منوی بیشتر:", reply_markup=get_more_keyboard())
            return
        if text.startswith(("➕", "🏠", "📅", "🕌", "💰", "🌤", "🛠", "🎮", "🎨", "👤", "🏙", "🌍", "🔙", "🤖")):
            if text != "🤖 دستیار هوشمند":
                context.user_data.pop("ai_mode", None)
                # fall through to normal menu handling
            else:
                # repeat the AI entry prompt
                providers = enabled_providers()
                provider_text = "، ".join(providers) if providers else "هیچ سرویس فعالی ندارد"
                await update.message.reply_text(
                    "🤖 دستیار هوشمند روز زیبا\n\n"
                    "پیامت را بفرست تا به هوش مصنوعی ارسال شود.\n"
                    f"سرویس‌های فعال: {provider_text}",
                    reply_markup=get_ai_keyboard(user_id),
                )
                return
        else:
            try:
                # فقط خواندن متن با ویس (بدون AI)
                import re as _re
                m_read = _re.match(r"^(بخون|بخوان)\s*[:：]?\s*(.+)$", text, _re.I | _re.S)
                if m_read:
                    to_read = m_read.group(2).strip()
                    try:
                        await _send_ai_voice(
                            update, to_read, user_id)
                    except Exception as ve:
                        await update.message.reply_text(f"⚠️ ویس ساخته نشد: {ve}")
                    return
                if looks_like_image_request(text):
                    notice = await update.message.reply_text("🎨 در حال ساخت تصویر...")
                    try:
                        img_bytes, mime = await generate_or_edit_image(text)
                        from io import BytesIO
                        bio = BytesIO(img_bytes)
                        bio.name = "ai_image.png" if "png" in mime else "ai_image.jpg"
                        await update.message.reply_photo(
                            photo=bio,
                            caption="🎨 تصویر ساخته شد",
                        )
                    finally:
                        try:
                            await notice.delete()
                        except Exception as _exc:
                            logger.debug("%s: %s", __name__, _exc)
                    return
                mode_msg = _apply_voice_chat_flags(context, text)
                if mode_msg:
                    await update.message.reply_text(mode_msg)
                # «ویس بفرست» بدون سؤال → آخرین جواب را با ویس بفرست
                if is_voice_only_request(text):
                    last = get_last_answer(user_id) or (context.user_data or {}).get("last_ai_answer")
                    if last:
                        try:
                            await _send_ai_voice(update, last, user_id)
                        except Exception as ve:
                            await update.message.reply_text(f"⚠️ ویس ساخته نشد: {ve}")
                    else:
                        await update.message.reply_text(
                            "هنوز جوابی برای خواندن ندارم. اول یک سؤال بپرس، بعد بگو «ویس بفرست»."
                        )
                    return
                voice_mode = wants_voice_reply(text) or bool(
                    context.user_data.get("ai_voice_chat")
                )
                ask_text = strip_voice_prefix(text) if wants_voice_reply(text) else text
                # اگر فقط روشن کردن حالت ویس بود و سؤال دیگری نبود، لازم نیست AI سنگین
                if mode_msg and wants_voice_chat_mode(text) and len(ask_text) < 40:
                    try:
                        await _send_ai_voice(
                            update,
                            "باشه، با ویس حرف می‌زنیم. هر وقت خواستی بگو.",
                            user_id,
                        )
                    except Exception as _exc:
                        logger.debug("%s: %s", __name__, _exc)
                    return
                # قابلیت‌های ویژه قبل از AI عمومی
                handled = await _handle_special_ai_intents(
                    update, context, user_id, ask_text
                )
                if handled:
                    return
                answer, provider = await _ask_ai_with_typing(
                    update, context, user_id, ask_text
                )
                if context.user_data is not None:
                    context.user_data["last_ai_answer"] = answer
                if not (context.user_data or {}).get("_ai_already_sent"):
                    await _send_ai_answer(update, user_id, answer, prompt=ask_text)
                if context.user_data is not None:
                    context.user_data.pop("_ai_already_sent", None)
                explicit = wants_voice_reply(text)
                if should_auto_voice_reply(
                    ask_text,
                    answer,
                    input_was_voice=False,
                    explicit_voice=explicit,
                    voice_chat_mode=bool(context.user_data.get("ai_voice_chat")),
                ):
                    try:
                        await _send_ai_voice(
                            update, answer, user_id
                        )
                    except Exception as ve:
                        await update.message.reply_text(
                            f"⚠️ متن آماده شد ولی ویس ساخته نشد: {ve}"
                        )
            except Exception as exc:
                await update.message.reply_text(
                    "❌ فعلاً هیچ‌کدام از سرویس‌های AI پاسخ ندادند.\n\n" + str(exc)[:3000]
                )
            return
    # Waiting workflows are dispatched by messages_waiting_dispatch after AI routing.
    # Do not reference an undefined legacy `waiting` variable here.
    return False
