"""دستورات مخصوص گروه: /ask /ai /groupsettings"""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from bot.logger import logger
from bot.handlers.group_mode import (
    is_group_chat,
    clean_group_prompt,
    get_bot_username,
    user_is_group_admin,
    settings_keyboard,
    group_ai_header,
)
from bot.handlers.group_settings import (
    get_group_settings,
    set_group_setting,
    is_group_ai_enabled,
)


async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /ask یا /ai — سؤال از هوش مصنوعی (گروه و پیوی) """
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if not message or not user:
        return

    args = context.args or []
    text = " ".join(args).strip() if args else ""

    # اگر بدون آرگومان و ریپلای به پیام باشد، از متن ریپلای استفاده کن
    if not text and message.reply_to_message:
        text = (message.reply_to_message.text or message.reply_to_message.caption or "").strip()

    if not text:
        await message.reply_text(
            "🧠 استفاده:\n"
            "`/ask سؤالت اینجاست`\n"
            "یا `/ai سؤالت`\n"
            "یا به یک پیام ریپلای کن و `/ask` بزن.",
            parse_mode="Markdown",
        )
        return

    if is_group_chat(chat):
        from bot.handlers.group_guard import group_ai_access_allowed, claim_group_update
        if not await group_ai_access_allowed(update, context, notify=True):
            return
        if not claim_group_update(update, context, namespace="command"):
            return
        bot_uname = get_bot_username(context)
        text = clean_group_prompt(text, bot_uname) or text

    try:
        from bot.handlers.group_stream import stream_ai_to_message
        await stream_ai_to_message(update, context, user.id, text)
    except Exception as exc:
        logger.warning("ask_command failed: %s", exc)
        await message.reply_text("⚠️ خطا در پاسخ. دوباره امتحان کن.")


async def groupsettings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تنظیمات گروه — فقط ادمین."""
    chat = update.effective_chat
    message = update.effective_message
    if not chat or not message:
        return
    if not is_group_chat(chat):
        await message.reply_text("این دستور فقط داخل گروه کار می‌کند.")
        return
    if not await user_is_group_admin(update, context):
        await message.reply_text("⛔ فقط ادمین‌های گروه می‌توانند تنظیمات را تغییر دهند.")
        return

    settings = get_group_settings(chat.id)
    ai = "✅ فعال" if settings.get("ai_enabled") else "❌ خاموش"
    short = "✅ بله" if settings.get("short_replies") else "❌ خیر"
    text = (
        f"⚙️ <b>تنظیمات گروه</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"🧠 هوش مصنوعی: <b>{ai}</b>\n"
        f"✂️ پاسخ کوتاه: <b>{short}</b>\n"
        f"📏 سقف کاراکتر: <code>{settings.get('max_answer_chars', 900)}</code>\n"
        f"━━━━━━━━━━━━━━\n"
        f"روی دکمه‌ها بزن تا تغییر کند."
    )
    await message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=settings_keyboard(chat.id, settings),
    )


async def group_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """کالبک‌های group_dismiss / group_help / group_settings / gset:"""
    q = update.callback_query
    if not q:
        return
    data = q.data or ""
    chat = update.effective_chat
    user = update.effective_user

    try:


        if data.startswith("gmusic:tr:"):
            key = data.split(":", 2)[-1].strip()
            try:
                await q.answer("در حال ترجمه…")
            except Exception:
                pass
            try:
                from bot.services.music_recognize import (
                    pop_lyrics_for_translate,
                    split_telegram_messages,
                )
                packed = pop_lyrics_for_translate(key)
            except Exception as exc:
                logger.warning("gmusic cache: %s", exc)
                packed = None
            if not packed:
                try:
                    await q.answer("مهلت ترجمه تمام شده؛ دوباره «ربات آهنگ» بزن.", show_alert=True)
                except Exception:
                    pass
                return
            lyrics_en = str(packed.get("lyrics") or "")
            header = str(packed.get("header") or "")
            msg_ids = list(packed.get("msg_ids") or [])
            chat_id = packed.get("chat_id")
            if not lyrics_en:
                # سازگاری قدیمی
                if isinstance(packed, tuple):
                    pass
                try:
                    await q.answer("متن آهنگ در کش نبود.", show_alert=True)
                except Exception:
                    pass
                return
            try:
                from bot.services.ai_service import ask_ai
                import re as _re
                uid = user.id if user else 0
                prompt = (
                    "تو مترجم ترانه هستی. این lyrics را کامل به فارسی محاوره‌ای، طبیعی و آهنگین ترجمه کن.\n"
                    "قوانین سخت:\n"
                    "1) کلمه به کلمه ممنوع — حس عاشقانه ترانه را حفظ کن\n"
                    "2) Baby, I'm yours = «عزیزم، مال توام» یا «بیبی، مال توام» — هرگز «بچه» نگو\n"
                    "3) You're so pretty, it hurts = «آن‌قدر زیبایی که درد داره»\n"
                    "4) ساختار بندها و تکرارها را کامل حفظ کن — هیچ بخشی را حذف نکن\n"
                    "5) فقط فارسی ترجمه؛ بدون عنوان و انگلیسی\n\n"
                    "متن آهنگ:\n" + lyrics_en[:8000]
                )
                tr = await ask_ai(uid, prompt)
                if isinstance(tr, tuple):
                    tr = tr[0]
                fa = str(tr or "").strip()
                fa = _re.sub(
                    r"^(?:ترجمه(?:\s*فارسی)?|persian\s*translation)\s*:?\s*",
                    "",
                    fa,
                    flags=_re.I,
                ).strip()
                fa_lines = []
                for ln in fa.splitlines():
                    if _re.search(r"[A-Za-z]{4,}", ln) and not _re.search(r"[\u0600-\u06FF]{2,}", ln):
                        continue
                    fa_lines.append(ln)
                fa = "\n".join(fa_lines).strip()
                if not fa or len(fa) < 15:
                    await q.answer("ترجمه در دسترس نبود.", show_alert=True)
                    return
                # هدر بدون متن انگلیسی
                if not header and q.message:
                    cur = q.message.text or q.message.caption or ""
                    if "📝" in cur:
                        header = cur.split("📝")[0].rstrip()
                    else:
                        header = cur
                # ساخت پیام‌های فارسی (کامل، چندتایی اگر لازم)
                fa_parts = split_telegram_messages(
                    header,
                    fa,
                    limit=3900,
                )
                # برچسب متن فارسی به‌جای «متن / زیرنویس»
                fa_parts = [
                    p.replace("📝 متن / زیرنویس:", "📝 متن فارسی:", 1).replace(
                        "📝 ادامه متن:", "📝 ادامه متن فارسی:", 1
                    )
                    for p in fa_parts
                ]
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                done_kb = InlineKeyboardMarkup(
                    [[InlineKeyboardButton("✅ ترجمه‌شده", callback_data="gmusic:done")]]
                )
                bot = context.bot
                # ویرایش پیام‌های قبلی
                edited = 0
                for idx, mid in enumerate(msg_ids):
                    try:
                        part = fa_parts[idx] if idx < len(fa_parts) else ""
                        if not part:
                            # پیام اضافه انگلیسی → پاک یا کوتاه کن
                            try:
                                await bot.edit_message_text(
                                    chat_id=chat_id or q.message.chat_id,
                                    message_id=mid,
                                    text="…",
                                    reply_markup=None,
                                )
                            except Exception:
                                pass
                            continue
                        is_last = idx == len(msg_ids) - 1 and idx == len(fa_parts) - 1
                        # اگر fa_parts بیشتر است، last در پیام آخر msg_ids نیست
                        is_last = (idx == len(msg_ids) - 1) and (len(fa_parts) <= len(msg_ids))
                        await bot.edit_message_text(
                            chat_id=chat_id or (q.message.chat_id if q.message else None),
                            message_id=mid,
                            text=part[:4090],
                            disable_web_page_preview=True,
                            reply_markup=(done_kb if is_last else None),
                        )
                        edited += 1
                    except Exception as e_one:
                        logger.warning("gmusic edit one failed mid=%s: %s", mid, e_one)
                # اگر ترجمه از پیام‌های اصلی بیشتر شد → پیام جدید
                if len(fa_parts) > max(1, len(msg_ids)):
                    start_i = len(msg_ids)
                    for idx in range(start_i, len(fa_parts)):
                        is_last = idx == len(fa_parts) - 1
                        await bot.send_message(
                            chat_id=chat_id or (q.message.chat_id if q.message else None),
                            text=fa_parts[idx][:4090],
                            disable_web_page_preview=True,
                            reply_markup=(done_kb if is_last else None),
                        )
                elif not msg_ids and q.message:
                    # فقط یک پیام callback
                    await q.edit_message_text(
                        fa_parts[0][:4090],
                        disable_web_page_preview=True,
                        reply_markup=done_kb,
                    )
                    for extra in fa_parts[1:]:
                        await q.message.reply_text(
                            extra[:4090],
                            disable_web_page_preview=True,
                            reply_markup=(done_kb if extra == fa_parts[-1] else None),
                        )
                if edited or fa_parts:
                    try:
                        await q.answer("ترجمه شد")
                    except Exception:
                        pass
            except Exception as exc:
                logger.warning("gmusic translate failed: %s", exc)
                try:
                    await q.answer("ترجمه ناموفق بود.", show_alert=True)
                except Exception:
                    pass
            return

        if data == "gmusic:done":
            try:
                await q.answer("قبلاً ترجمه شده")
            except Exception:
                pass
            return

        if data == "group_dismiss":
            await q.answer("حذف شد")
            try:
                await q.message.delete()
            except Exception:
                try:
                    await q.edit_message_reply_markup(reply_markup=None)
                except Exception:
                    pass
            return

        if data == "group_help":
            await q.answer()
            uname = get_bot_username(context) or "bot"
            await q.message.reply_text(
                f"🧠 در گروه:\n"
                f"• منشن: @{uname} سؤالت\n"
                f"• ریپلای به پیام من\n"
                f"• دستور: /ask سؤالت  یا  /ai سؤالت\n"
                f"• پیشوند: ! سؤالت\n\n"
                f"⚙️ ادمین: /groupsettings\n"
                f"برای منوی کامل بهم تو پیوی پیام بده.",
                disable_web_page_preview=True,
            )
            return

        if data == "group_settings_open":
            if not is_group_chat(chat):
                await q.answer("این دکمه فقط داخل گروه معتبر است.", show_alert=True)
                return
            if not await user_is_group_admin(update, context):
                await q.answer("فقط ادمین", show_alert=True)
                return
            await q.answer()
            settings = get_group_settings(chat.id)
            ai = "✅ فعال" if settings.get("ai_enabled") else "❌ خاموش"
            short = "✅ بله" if settings.get("short_replies") else "❌ خیر"
            text = (
                f"⚙️ <b>تنظیمات گروه</b>\n"
                f"🧠 AI: <b>{ai}</b>\n"
                f"✂️ کوتاه: <b>{short}</b>"
            )
            await q.message.reply_text(
                text, parse_mode="HTML", reply_markup=settings_keyboard(chat.id, settings)
            )
            return

        if data.startswith("gset:"):
            # gset:KEY:CHATID
            if not await user_is_group_admin(update, context):
                await q.answer("فقط ادمین گروه", show_alert=True)
                return
            parts = data.split(":")
            if len(parts) < 3:
                await q.answer()
                return
            kind, chat_id_s = parts[1], parts[2]
            # سازگاری با کلیدهای قدیمی
            alias = {"ai": "ai_enabled", "short": "short_replies"}
            kind = alias.get(kind, kind)
            try:
                chat_id = int(chat_id_s)
            except ValueError:
                await q.answer()
                return
            # دکمه‌های یک گروه نباید از گروه/گفت‌وگوی دیگری قابل استفاده باشند.
            if not chat or not is_group_chat(chat) or int(chat.id) != chat_id:
                await q.answer("این دکمه متعلق به گروه دیگری است.", show_alert=True)
                return
            settings = get_group_settings(chat_id)
            if kind not in settings and kind not in ("ai_enabled", "short_replies", "fast_path", "mention_only", "admin_only"):
                await q.answer()
                return
            cur = int(settings.get(kind, 0) or 0)
            new_val = 0 if cur else 1
            if not set_group_setting(chat_id, kind, new_val, updated_by=user.id if user else None):
                await q.answer("ذخیره تنظیمات انجام نشد؛ دیتابیس را بررسی کن.", show_alert=True)
                return
            labels = {
                "ai_enabled": "AI",
                "short_replies": "پاسخ کوتاه",
                "fast_path": "Fast-path",
                "mention_only": "فقط منشن",
                "admin_only": "فقط ادمین",
            }
            await q.answer(f"{labels.get(kind, kind)} → {'روشن' if new_val else 'خاموش'}")
            settings = get_group_settings(chat_id)
            text = (
                f"⚙️ <b>تنظیمات گروه</b>\n"
                f"━━━━━━━━━━━━━━\n"
                f"🧠 AI: <b>{'✅' if settings.get('ai_enabled') else '❌'}</b>\n"
                f"✂️ کوتاه: <b>{'✅' if settings.get('short_replies') else '❌'}</b>\n"
                f"⚡ Fast-path: <b>{'✅' if settings.get('fast_path') else '❌'}</b>\n"
                f"📌 فقط منشن: <b>{'✅' if settings.get('mention_only') else '❌'}</b>\n"
                f"👮 فقط ادمین: <b>{'✅' if settings.get('admin_only') else '❌'}</b>"
            )
            try:
                await q.edit_message_text(
                    text, parse_mode="HTML", reply_markup=settings_keyboard(chat_id, settings)
                )
            except Exception:
                pass
            return

    except Exception as exc:
        logger.debug("group_callback_handler: %s", exc)
        try:
            await q.answer()
        except Exception:
            pass



async def group_quick_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دکمه‌های سریع UX گروه: دلار/طلا/BTC/هوا."""
    q = update.callback_query
    if not q or not q.data:
        return
    data = q.data
    if not data.startswith("gquick:"):
        return
    if not is_group_chat(update.effective_chat):
        await q.answer("این دکمه فقط داخل گروه معتبر است.", show_alert=True)
        return
    await q.answer()
    kind = data.split(":", 1)[-1]
    mapping = {
        "dollar": "قیمت دلار",
        "gold": "قیمت طلا",
        "btc": "قیمت بیتکوین",
        "weather": "هوای تهران",
    }
    prompt = mapping.get(kind)
    if not prompt:
        return
    try:
        from bot.handlers.group_parts.fast_path import run_fast_path
        from bot.handlers.group_parts.group_ui import kb_price
        fp = await run_fast_path(prompt)
        if fp:
            await q.message.reply_text(fp, parse_mode="HTML", reply_markup=kb_price())
        else:
            await q.message.reply_text("الان موجود نبود. دوباره بپرس: " + prompt)
    except Exception as exc:
        from bot.logger import logger
        logger.warning("gquick failed: %s", exc)
