from telegram import Update
from telegram.ext import ContextTypes

# Auto-split part 2: voice_ai_handler
async def voice_ai_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ویس/صوت ورودی کاربر → متن → جواب AI (و در صورت تمایل ویس خروجی)."""
    # Imported lazily to avoid a circular import with messages.py compatibility facade.
    from bot.handlers.messages import (
        _send_ai_answer, _send_ai_voice, _ask_ai_with_typing, _apply_voice_chat_flags,
    )
    if not update.message:
        return
    if not await check_and_rate_limit(update, context):
        return
    if not context.user_data.get("ai_mode"):
        return

    user_id = update.effective_user.id
    msg = update.message
    caption = (msg.caption or "").strip()

    try:
        if msg.voice:
            tg_file = await msg.voice.get_file()
            data = bytes(await tg_file.download_as_bytearray())
            filename, mime = "voice.ogg", "audio/ogg"
        elif msg.audio:
            tg_file = await msg.audio.get_file()
            data = bytes(await tg_file.download_as_bytearray())
            filename = msg.audio.file_name or "audio.mp3"
            mime = msg.audio.mime_type or "audio/mpeg"
        elif msg.video_note:
            # دایره ویدیویی — فقط صدا را نداریم؛ رد می‌کنیم یا download full
            await msg.reply_text("لطفاً ویس معمولی بفرست (نه ویدیو نوت).")
            return
        else:
            return

        if len(data) > 15 * 1024 * 1024:
            await msg.reply_text("❌ حجم ویس خیلی زیاد است.")
            return

        notice = await msg.reply_text("🎧 در حال پیاده‌سازی ویس...")
        try:
            transcript = await speech_to_text(data, filename=filename, mime=mime)
        finally:
            try:
                await notice.delete()
            except Exception:
                pass

        if not transcript:
            await msg.reply_text("❌ چیزی از ویس متوجه نشدم. دوباره واضح‌تر بفرست.")
            return

        # اگر کپشن داشت به متن اضافه کن
        user_text = transcript
        if caption:
            user_text = caption + "\n\n(متن ویس): " + transcript

        await msg.reply_text("📝 شنیدم:\n" + transcript)

        # تشخیص احساس فقط اگر کاربر خواسته باشد
        want_emo = wants_emotion_analysis(caption) or wants_emotion_analysis(transcript)
        if want_emo:
            try:
                emo_notice = await msg.reply_text("💗 در حال تشخیص احساس از صدا...")
                emotion = await analyze_voice_emotion(
                    data, transcript=transcript, filename=filename, mime=mime
                )
                try:
                    await emo_notice.delete()
                except Exception:
                    pass
                await msg.reply_text("🎭 تحلیل احساس صدا:\n" + emotion)
                user_text = (
                    user_text
                    + "\n\n[تحلیل احساس صدای کاربر]\n"
                    + emotion
                )
            except Exception as ee:
                try:
                    await emo_notice.delete()
                except Exception:
                    pass
                from bot.logger import logger
                logger.warning("emotion detect failed: %s", ee)

        # حالت مکالمه ویسی از روی متن ویس یا کپشن
        combined_for_mode = ((caption or "") + " " + (transcript or "")).strip()
        mode_msg = _apply_voice_chat_flags(context, combined_for_mode)
        if mode_msg:
            await msg.reply_text(mode_msg, reply_markup=get_ai_keyboard(user_id))

        # ورودی ویس به خودی خود مکالمه را به سمت ویس می‌برد
        if not context.user_data.get("ai_voice_chat"):
            # اگر گفت ویس حرف بزنیم یا کلاً ویس فرستاد برای گپ، حالت را نرم روشن کن
            if wants_voice_chat_mode(combined_for_mode):
                context.user_data["ai_voice_chat"] = True

        explicit_voice = bool(
            wants_voice_reply(caption or "")
            or wants_voice_reply(transcript or "")
            or context.user_data.get("ai_always_voice")
        )
        voice_chat = bool(context.user_data.get("ai_voice_chat"))

        # اگر فقط درخواست شروع حالت ویس بود
        if mode_msg and wants_voice_chat_mode(combined_for_mode) and len(transcript) < 50:
            try:
                await _send_ai_voice(
                    msg,
                    "باشه، با ویس حرف می‌زنیم. هر وقت خواستی بگو.",
                    user_id,
                )
            except Exception as ve:
                await msg.reply_text(f"⚠️ {ve}")
            return

        # ترجمه زنده ویس
        import re as _re
        tr = _re.search(
            r"ترجمه\s*(به)?\s*(انگلیسی|فارسی|عربی|ترکی|آلمانی|فرانسوی|en|fa|ar|tr|de|fr)?",
            (caption or "") + " " + (transcript or ""),
            _re.I,
        )
        if tr or _re.search(r"\btranslate\b", (caption or ""), _re.I):
            lang_map = {
                "انگلیسی": "en", "en": "en", "فارسی": "fa", "fa": "fa",
                "عربی": "ar", "ar": "ar", "ترکی": "tr", "tr": "tr",
                "آلمانی": "de", "de": "de", "فرانسوی": "fr", "fr": "fr",
            }
            target = "en"
            if tr and tr.group(2):
                target = lang_map.get(tr.group(2).lower(), "en")
            notice = await msg.reply_text("🌐 در حال ترجمه ویس...")
            try:
                src, dst, audio = await translate_voice(
                    data, target_lang=target, filename=filename, mime=mime
                )
                await msg.reply_text(f"📝 اصلی:\n{src}\n\n🌐 ترجمه:\n{dst}")
                from io import BytesIO
                bio = BytesIO(audio)
                bio.name = "tr.mp3"
                await msg.reply_audio(audio=bio, caption="🔊 ترجمه صوتی")
            except Exception as e:
                await msg.reply_text(f"⚠️ ترجمه: {e}")
            finally:
                try:
                    await notice.delete()
                except Exception:
                    pass
            return

        answer, provider = await _ask_ai_with_typing(
            update, context, user_id, user_text
        )
        if not (context.user_data or {}).get("_ai_already_sent"):
            await _send_ai_answer(update, user_id, answer)
        if context.user_data is not None:
            context.user_data.pop("_ai_already_sent", None)
        if should_auto_voice_reply(
            user_text,
            answer,
            input_was_voice=True,
            explicit_voice=explicit_voice,
            voice_chat_mode=bool(voice_chat),  # فقط اگر حالت ویس روشن باشد
        ):
            try:
                await _send_ai_voice(
                    msg, answer, user_id
                )
            except Exception as ve:
                await msg.reply_text(f"⚠️ ویس خروجی ساخته نشد: {ve}")
    except Exception as exc:
        await msg.reply_text(
            "❌ پردازش ویس ممکن نشد.\n\n" + str(exc)[:2500],
            reply_markup=get_ai_keyboard(user_id),
        )
