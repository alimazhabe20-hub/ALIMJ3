"""Group-specific multimodal AI pipeline (photo, video, documents, audio/voice)."""
from __future__ import annotations

import re
from typing import Optional

from bot.logger import logger

MAX_GROUP_MEDIA_BYTES = 18 * 1024 * 1024


def _is_garbage_transcript(text: str) -> bool:
    """فقط وقتی متن واقعاً بی‌معنی/تکراری است True بده — نه هر STT ناقص."""
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    if not t or len(t) < 2:
        return True
    words = t.split()
    # تکرار شدید یک/دو کلمه
    if len(words) >= 6:
        uniq = set(w.lower() for w in words)
        if len(uniq) <= 2:
            return True
    if t.count("موسیقی") >= 4:
        return True
    # فقط کدهای لاتین کوتاه بدون فارسی
    fa = re.findall(r"[\u0600-\u06FF]{2,}", t)
    latin_tokens = re.findall(r"[A-Za-z]{2,}", t)
    if not fa and latin_tokens and len(words) <= 5 and len(t) <= 30:
        return True
    return False


def _wants_voice_analysis(caption: str) -> bool:
    c = (caption or "").strip()
    return bool(re.search(r"تحلیل|توضیح|احساس|لحن|چیه|بگو|summar|analy|emotion", c, re.I))


def _sanitize_history(history: str, limit: int = 1200) -> str:
    raw = str(history or "")
    bad = (
        "دستیار:", "کاربر:", "زمینه گروه", "متن پیاده‌شده", "متن پیاده شده",
        "نتیجهٔ قابل‌اعتماد", "نتیجه قابل‌اعتماد", "digikala.com", "torob.com",
        "[SHOPPING", "[قوانین پاسخ", "[زمینه کوتاه",
    )
    lines = []
    for ln in raw.splitlines():
        s = ln.strip()
        if not s:
            continue
        if any(b in s for b in bad):
            continue
        if _is_garbage_transcript(s):
            continue
        lines.append(s)
    out = "\n".join(lines)
    return out[-limit:] if len(out) > limit else out



def _speaker(update) -> str:
    user = update.effective_user
    if not user:
        return "عضو گروه"
    return (getattr(user, "full_name", None) or getattr(user, "first_name", None) or "عضو گروه")[:80]


def _is_supported_media(message) -> bool:
    return bool(
        getattr(message, "photo", None) or getattr(message, "video", None)
        or getattr(message, "video_note", None) or getattr(message, "document", None)
        or getattr(message, "voice", None) or getattr(message, "audio", None)
        or getattr(message, "sticker", None)
    )


async def handle_group_media(update, context, *, source_message=None, prompt: str = "") -> bool:
    """Process group media only when group response rules permit it."""
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    source = source_message or message
    if not message or not chat or not user or not source or not _is_supported_media(source):
        return False

    from bot.handlers.group_mode import is_group_chat, should_respond_in_group
    if not is_group_chat(chat):
        return False

    # For media replies, the command/caption on the invoking message controls the gate.
    ok, reason = should_respond_in_group(update, context)
    if not ok:
        # A captionless media message must not trigger an unsolicited AI response.
        return False
    try:
        from bot.handlers.group_settings import group_admin_only
        if group_admin_only(chat.id):
            from bot.handlers.group_mode import user_is_group_admin
            if not await user_is_group_admin(update, context):
                return False
    except Exception as exc:
        logger.warning("group media admin gate failed closed: %s", exc)
        return False

    caption = (prompt or getattr(message, "caption", None) or "").strip()
    reply = getattr(message, "reply_to_message", None)
    reply_context = ""
    if reply and reply is not source:
        replied_text = (getattr(reply, "text", None) or getattr(reply, "caption", None) or "").strip()
        if replied_text:
            reply_context = f"\n\nمتنی که به آن Reply شده: {replied_text[:1800]}"

    from bot.handlers.group_settings import is_group_ai_enabled
    if not is_group_ai_enabled(chat.id):
        return False

    from bot.handlers.group_parts.group_memory import add_turn, get_context
    speaker = _speaker(update)
    user_id = user.id
    media_label = "رسانهٔ پیوست‌شده"
    data = b""
    mime = "application/octet-stream"
    images = []
    file_text = None
    filename = ""
    notice = None

    try:
        if source.photo:
            media = source.photo[-1]
            mime = "image/jpeg"
            media_label = "تصویر"
        elif source.document:
            media = source.document
            filename = source.document.file_name or "document"
            mime = source.document.mime_type or "application/octet-stream"
            media_label = f"فایل {filename}"
        elif source.video or source.video_note:
            media = source.video or source.video_note
            mime = getattr(media, "mime_type", None) or "video/mp4"
            media_label = "ویدیو"
        elif source.voice or source.audio:
            media = source.voice or source.audio
            mime = getattr(media, "mime_type", None) or ("audio/ogg" if source.voice else "audio/mpeg")
            filename = getattr(media, "file_name", None) or ("voice.ogg" if source.voice else "audio.mp3")
            media_label = "پیام صوتی"
        elif source.sticker:
            media = source.sticker
            mime = "image/webp"
            media_label = "استیکر"
        else:
            return False

        file_obj = await media.get_file()
        data = bytes(await file_obj.download_as_bytearray())
        if not data:
            await message.reply_text("⚠️ نتوانستم فایل رسانه را دریافت کنم.")
            return True
        if len(data) > MAX_GROUP_MEDIA_BYTES:
            await message.reply_text("⚠️ حجم این فایل برای تحلیل گروهی بیش از حد مجاز است (۱۸ مگابایت).")
            return True

        if source.video or source.video_note:
            notice = await message.reply_text("🎬 در حال بررسی ویدیو...")
            from bot.services.ai_service import analyze_video
            result = await analyze_video(data, (caption or "این ویدیو را به فارسی تحلیل و خلاصه کن.") + reply_context, mime=mime)
        elif source.voice or source.audio:
            notice = await message.reply_text("🎧 در حال تبدیل صدا به متن و تحلیل...")
            from bot.services.ai_service import speech_to_text, ask_ai
            transcript = ""
            try:
                transcript = (await speech_to_text(data, filename=filename, mime=mime) or "").strip()
            except Exception as stt_exc:
                logger.warning("group STT failed: %s", stt_exc)
                transcript = ""
            garbage = _is_garbage_transcript(transcript)
            wants_analysis = _wants_voice_analysis(caption) or _wants_voice_analysis(prompt)
            cap_all = f"{caption or ''} {prompt or ''}"
            result = None
            _music_tr_key = ""

            # ── شناسایی آهنگ + lyrics ─────────────────────────────
            try:
                from bot.services.music_recognize import (
                    wants_music_id,
                    wants_lyrics,
                    identify_and_lyrics,
                )
                music_req = wants_music_id(cap_all) or wants_lyrics(cap_all)
                short_cmd = re.sub(r"^(?:ربات|هوشمند|!)\s*", "", (cap_all or "").strip(), flags=re.I)
                short_cmd = short_cmd.replace("اهنگ", "آهنگ").strip()
                # STT خراب + نشانه موسیقی/درخواست آهنگ
                looks_like_music = garbage and (
                    music_req
                    or "موسیقی" in (transcript or "")
                    or wants_music_id(short_cmd)
                    or short_cmd in {"آهنگ", "music", "song"}
                )
                if music_req or looks_like_music:
                    try:
                        result = identify_and_lyrics(
                            data,
                            filename=filename,
                            mime=mime,
                            want_lyrics=True,
                            chat_id=getattr(getattr(update, "effective_chat", None), "id", None),
                            transcript_hint=(transcript or "")[:800],
                        )
                        # ترجمه فارسی با دکمه اینلاین (نه خودکار)
                        try:
                            from bot.services.music_recognize import (
                                extract_lyrics_block,
                                store_lyrics_for_translate,
                            )
                            lyrics_en = extract_lyrics_block(str(result))
                            if lyrics_en and len(lyrics_en) > 20:
                                _music_tr_key = store_lyrics_for_translate(str(result), lyrics_en)
                            else:
                                _music_tr_key = ""
                        except Exception as _sk:
                            logger.debug("music tr key store: %s", _sk)
                            _music_tr_key = ""

                    except RuntimeError as rexc:
                        if "AUDD" in str(rexc).upper() and music_req:
                            result = (
                                "🎵 برای شناسایی آهنگ باید AUDD_API_TOKEN "
                                "روی سرور ست شود.\n"
                                "ثبت‌نام رایگان: https://dashboard.audd.io/"
                            )
                        else:
                            logger.warning("music recognize: %s", rexc)
                    except Exception as mexc:
                        logger.warning("music recognize failed: %s", mexc)
            except Exception as exc:
                logger.debug("music module unavailable: %s", exc)

            if result:
                pass  # already have music/ID answer
            elif garbage and wants_analysis:
                try:
                    from bot.services.ai_service import analyze_voice_emotion
                    emotion = await analyze_voice_emotion(
                        data, transcript="", filename=filename, mime=mime
                    )
                    result = (
                        "🎧 تحلیل مستقیم صدا (متن گفتار واضح نبود):\n\n"
                        + str(emotion or "تحلیل احساس انجام نشد.")[:3500]
                    )
                except Exception as em_exc:
                    logger.warning("voice emotion fallback failed: %s", em_exc)
                    result = (
                        "⚠️ متن گفتار واضح نبود و تحلیل مستقیم صدا هم الان ممکن نشد.\n"
                        "برای آهنگ بنویس: «ربات این آهنگ چیه» یا «ربات متن آهنگ»\n"
                        "برای حرف معمولی با صدای واضح‌تر بفرست."
                    )
            elif garbage:
                result = (
                    "⚠️ متن این ویس واضح تشخیص داده نشد.\n"
                    "اگر آهنگ است بنویس: «ربات این آهنگ چیه» یا «ربات متن آهنگ»\n"
                    "اگر حرف است: «ربات تحلیل» یا همان را تایپ کن."
                )
            else:
                history = get_context(
                    chat.id,
                    user_id=user_id,
                    reply_to_message_id=getattr(reply, "message_id", None),
                )
                history = _sanitize_history(history, limit=1200)
                task = (caption or "").strip()
                if not task or len(task) <= 3 or task in {"؟", "?", "الس؟", "الس"}:
                    task = "گفتار این فایل صوتی را خلاصه کن و اگر سؤال/درخواستی دارد کوتاه جواب بده."
                elif re.search(r"^\s*(?:ربات\s*)?تحلیل\s*$", task, re.I):
                    task = "این پیام صوتی را تحلیل کن: محتوا، منظور، و لحن گوینده را کوتاه بگو."
                ai_prompt = (
                    f"{task}\n\n"
                    f"متن پیاده‌شده از صدای {speaker}:\n{transcript[:1500]}\n"
                )
                if history:
                    ai_prompt += f"\nزمینه کوتاه گروه (فقط برای فهم، تکرار نکن):\n{history}\n"
                ai_prompt += (
                    "\nقوانین: اگر سؤال خرید کالا نیست جستجوی فروشگاه نکن. "
                    "پاسخ کوتاه و مفید به فارسی بده."
                )
                result = await ask_ai(user_id, ai_prompt)
                if isinstance(result, tuple):
                    result = result[0]
                rs = str(result or "")
                if "digikala.com/search" in rs or "torob.com/search" in rs or "نتیجهٔ قابل‌اعتماد" in rs or "نتیجه قابل‌اعتماد" in rs:
                    result = (
                        f"شنیدم این را: «{transcript[:200]}»\n"
                        "اگر منظورت چیز دیگری است همان را کوتاه بنویس."
                    )
                else:
                    result = f"📝 متن گفتار:\n{transcript[:2500]}\n\n🤖 پاسخ:\n{result}"

        else:
            notice = await message.reply_text("🔎 در حال تحلیل رسانه...")
            if mime.startswith("image/") or media_label in ("تصویر", "استیکر"):
                images = [(data, mime)]
            else:
                # Reuse the project's document extraction service for PDF/DOCX/TXT/CSV/etc.
                try:
                    from bot.services.v72_platform import extract_document, document_context
                    rich = extract_document(data, filename or "file", mime)
                    file_text = document_context(rich)
                except Exception as exc:
                    logger.warning("group document extraction failed: %s", exc)
                    try:
                        from bot.handlers.media_handlers import _extract_text_from_bytes
                        file_text = _extract_text_from_bytes(data, filename, mime)
                    except Exception:
                        file_text = ""
                if not file_text:
                    await message.reply_text("⚠️ قالب این فایل پشتیبانی نمی‌شود یا متن قابل استخراج ندارد.")
                    return True

            history = get_context(chat.id, user_id=user_id, reply_to_message_id=getattr(reply, "message_id", None))
            task = caption or ("این تصویر را توصیف و تحلیل کن." if images else "این فایل را خلاصه و نکات مهمش را استخراج کن.")
            task += reply_context
            if history:
                task = f"زمینه مکالمه گروه (برای رفع ارجاع‌ها):\n{history[-4000:]}\n\nدرخواست فعلی از طرف {speaker}:\n{task}"
            from bot.services.ai_service import ask_ai_media
            result = await ask_ai_media(user_id, task, images=images or None, file_text=file_text, filename=filename)
            if isinstance(result, tuple):
                result = result[0]

        answer = str(result or "پاسخی از مدل دریافت نشد.").strip()
        add_turn(chat.id, "user", f"[{media_label}] {caption or 'درخواست تحلیل رسانه'}", user_id=user_id, speaker=speaker, message_id=getattr(message, "message_id", None), reply_to_message_id=getattr(reply, "message_id", None))
        add_turn(chat.id, "bot", answer, user_id=None, speaker="روز زیبا", message_id=None)
        # Telegram messages are limited to 4096 chars.
        prefix = f"🤖 پاسخ به {speaker}:\n"
        body = (prefix + answer).strip()
        try:
            if locals().get("_music_tr_key"):
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                from bot.services.music_recognize import (
                    extract_lyrics_block,
                    split_telegram_messages,
                    bind_lyrics_messages,
                    store_lyrics_for_translate,
                )
                import re as _re_h
                lyrics_en = extract_lyrics_block(str(answer))
                hm = _re_h.search(
                    r"(.*?)(?:📝\s*متن(?:\s*/\s*زیرنویس)?\s*:?)\s*",
                    str(answer),
                    flags=_re_h.S,
                )
                header_core = hm.group(1).rstrip() if hm else str(answer).split("📝")[0]
                header_only = (prefix + header_core).strip()
                if lyrics_en and len(lyrics_en) > 20:
                    _music_tr_key = store_lyrics_for_translate(
                        str(answer), lyrics_en, header=header_only
                    ) or _music_tr_key
                    parts = split_telegram_messages(header_only, lyrics_en, limit=3900)
                else:
                    parts = [body[:4090]]
                kb = None
                if _music_tr_key:
                    kb = InlineKeyboardMarkup(
                        [[
                            InlineKeyboardButton(
                                "🇮🇷 ترجمه فارسی",
                                callback_data=f"gmusic:tr:{_music_tr_key}",
                            )
                        ]]
                    )
                msg_ids = []
                for idx, part in enumerate(parts):
                    is_last = idx == len(parts) - 1
                    sent = await message.reply_text(
                        part[:4090],
                        disable_web_page_preview=True,
                        reply_markup=(kb if is_last else None),
                    )
                    if sent and getattr(sent, "message_id", None):
                        msg_ids.append(int(sent.message_id))
                if _music_tr_key and msg_ids:
                    bind_lyrics_messages(
                        _music_tr_key,
                        getattr(chat, "id", None) or 0,
                        msg_ids,
                    )
            else:
                await message.reply_text(body[:4090], disable_web_page_preview=True)
        except Exception as send_exc:
            logger.warning("music multi-send failed: %s", send_exc)
            try:
                await message.reply_text(body[:4090], disable_web_page_preview=True)
            except Exception:
                pass
        return True
    except Exception as exc:
        logger.warning("group media processing failed chat=%s user=%s: %s", chat.id, user_id, exc)
        try:
            await message.reply_text("⚠️ تحلیل این رسانه انجام نشد. لطفاً فایل کوتاه‌تر یا واضح‌تری بفرست و دوباره درخواست کن.")
        except Exception:
            pass
        return True
    finally:
        if notice:
            try:
                await notice.delete()
            except Exception:
                pass
