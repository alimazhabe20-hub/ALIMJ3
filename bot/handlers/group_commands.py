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
        if not is_group_ai_enabled(chat.id):
            await message.reply_text("⏸ AI در این گروه خاموش است. ادمین: /groupsettings")
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
            await q.answer()
            if not is_group_chat(chat):
                return
            if not await user_is_group_admin(update, context):
                await q.answer("فقط ادمین", show_alert=True)
                return
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
            # gset:ai:CHATID  or  gset:short:CHATID
            if not await user_is_group_admin(update, context):
                await q.answer("فقط ادمین گروه", show_alert=True)
                return
            parts = data.split(":")
            if len(parts) < 3:
                await q.answer()
                return
            kind, chat_id_s = parts[1], parts[2]
            try:
                chat_id = int(chat_id_s)
            except ValueError:
                await q.answer()
                return
            settings = get_group_settings(chat_id)
            if kind == "ai":
                new_val = 0 if settings.get("ai_enabled") else 1
                set_group_setting(chat_id, "ai_enabled", new_val, updated_by=user.id if user else None)
                await q.answer("AI " + ("فعال شد ✅" if new_val else "خاموش شد"))
            elif kind == "short":
                new_val = 0 if settings.get("short_replies") else 1
                set_group_setting(chat_id, "short_replies", new_val, updated_by=user.id if user else None)
                await q.answer("پاسخ کوتاه " + ("فعال ✅" if new_val else "خاموش"))
            else:
                await q.answer()
                return
            settings = get_group_settings(chat_id)
            ai = "✅ فعال" if settings.get("ai_enabled") else "❌ خاموش"
            short = "✅ بله" if settings.get("short_replies") else "❌ خیر"
            text = (
                f"⚙️ <b>تنظیمات گروه</b>\n"
                f"━━━━━━━━━━━━━━\n"
                f"🧠 هوش مصنوعی: <b>{ai}</b>\n"
                f"✂️ پاسخ کوتاه: <b>{short}</b>\n"
                f"📏 سقف: <code>{settings.get('max_answer_chars', 900)}</code>"
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
