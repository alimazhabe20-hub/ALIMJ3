"""Semantic message-routing handlers. Extracted from the legacy text handler without removing behavior."""
from .messages_common import *  # noqa: F401,F403
from . import messages_common as _common
from .messages_main import _send_main
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})

def _is_back(text):
    t = text.strip()
    return t in ("🔙 بازگشت", "بازگشت") or "بازگشت" in t

def _is_back_more(text):
    return "بازگشت به بیشتر" in text

async def handle_profile_menu(update, context, text, user_id, city=None, first_name=None):
    # پروفایل
    if text in ("⏰ مدیریت یادآوری‌ها", "مدیریت یادآوری‌ها"):
        await _h_reminder_manager(update, context, user_id)
        return
    if text in ("⚙️ تنظیمات هوشمند", "تنظیمات هوشمند"):
        from bot.database import get_user_preferences
        prefs = get_user_preferences(user_id)
        style_names = {"short": "کوتاه", "balanced": "متعادل", "long": "کامل"}
        await update.message.reply_text(
            "⚙️ تنظیمات هوشمند\n\n"
            f"✍️ سبک پاسخ: {style_names.get(prefs.get('response_style'), 'متعادل')}\n"
            f"💵 ارز پیش‌فرض: {prefs.get('currency', 'USD')}\n\n"
            "این تنظیمات فقط برای شخصی‌سازی تجربه استفاده می‌شوند.",
            reply_markup=get_smart_settings_keyboard(),
        )
        return
    if text in ("✍️ پاسخ کوتاه", "📚 پاسخ کامل", "⚖️ پاسخ متعادل"):
        from bot.database import set_user_preference
        style = "short" if "کوتاه" in text else "long" if "کامل" in text else "balanced"
        set_user_preference(user_id, "response_style", style)
        await update.message.reply_text("✅ سبک پاسخ ذخیره شد.", reply_markup=get_smart_settings_keyboard())
        return
    if text in ("💵 ارز USD", "💶 ارز EUR", "🇮🇷 ارز IRR"):
        from bot.database import set_user_preference
        currency = text.split()[-1]
        set_user_preference(user_id, "currency", currency)
        await update.message.reply_text(f"✅ ارز پیش‌فرض: {currency}", reply_markup=get_smart_settings_keyboard())
        return
    if text == "🔄 بررسی بروزرسانی":
        try:
            from bot.handlers.v78_handlers import update_center_command
            await update_center_command(update, context)
        except Exception as exc:
            logger.warning("update center failed from smart settings: %s", exc, exc_info=True)
            await update.message.reply_text("⚠️ بررسی بروزرسانی فعلاً در دسترس نیست.", reply_markup=get_smart_settings_keyboard())
        return
    if text == "🧹 پاک‌سازی تنظیمات":
        from bot.database import clear_user_preferences
        clear_user_preferences(user_id)
        await update.message.reply_text("🧹 تنظیمات هوشمند پاک شد.", reply_markup=get_smart_settings_keyboard())
        return
    if text == "🔙 بازگشت به پروفایل":
        await update.message.reply_text("👤 پروفایل:", reply_markup=get_profile_keyboard())
        return
    if text in ("👤 پروفایل من", "پروفایل من"):
        track_usage(user_id, "profile")
        u = update.effective_user
        txt = profile_text(
            user_id, u.first_name or first_name,
            username=u.username, last_name=u.last_name,
            language_code=getattr(u, "language_code", None),
        )
        try:
            photos = await context.bot.get_user_profile_photos(user_id, limit=1)
            if photos.total_count > 0:
                file_id = photos.photos[0][-1].file_id
                await update.message.reply_photo(file_id, caption=txt.replace("**", "").replace("`","")+ "", reply_markup=get_profile_keyboard())
            else:
                await update.message.reply_text(txt.replace("**", "").replace("`",""), reply_markup=get_profile_keyboard())
        except Exception:
            await update.message.reply_text(txt.replace("**", "").replace("`",""), reply_markup=get_profile_keyboard())
        return
    if text in ("📊 آمار من", "آمار من"):
        track_usage(user_id, "stats")
        usage = get_user_usage(user_id) or []
        if usage:
            lines = []
            for row in usage[:15]:
                try:
                    lines.append(f"• {row[0]}: {row[1]}")
                except Exception as _exc:
                    logger.debug("%s: %s", __name__, _exc)
            msg = "📊 آمار:\n" + ("\n".join(lines) if lines else "خالی")
        else:
            msg = "📊 آمار:\nخالی"
        await update.message.reply_text(msg, reply_markup=get_profile_keyboard()); return
    if text in ("🎂 ذخیره تاریخ تولد", "ذخیره تاریخ تولد"):
        context.user_data["waiting_for"] = "birth_save"
        await update.message.reply_text("🎂 `1375/03/15`", reply_markup=get_profile_keyboard()); return
    if text in ("🇮🇷 ایران", "ایران"):
        await update.message.reply_text("🇮🇷 شهر:", reply_markup=get_iran_cities_keyboard()); return
    if text in ("🇮🇶 عراق", "عراق"):
        await update.message.reply_text("🇮🇶 شهر:", reply_markup=get_iraq_cities_keyboard()); return
    if _is_back(text):
        await _send_main(update, context, await build_message(user_id, first_name, city), user_id); return
    return False
