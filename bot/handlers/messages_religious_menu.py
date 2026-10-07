"""Semantic message-routing handlers. Extracted from the legacy text handler without removing behavior."""
from .messages_common import *  # noqa: F401,F403
from . import messages_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})

async def handle_religious_menu(update, context, text, user_id, city=None, first_name=None):
    # مذهبی
    if text in ("🕋 قبله‌نما", "قبله‌نما"):
        track_usage(user_id, "qibla")
        await update.message.reply_text(qibla_direction(city), reply_markup=get_religious_keyboard()); return
    if text in ("📿 اذکار روز", "اذکار روز"):
        track_usage(user_id, "adhkar")
        await update.message.reply_text(daily_adhkar(user_id), reply_markup=get_religious_keyboard()); return
    if text in ("📖 آیه و حدیث", "آیه و حدیث"):
        track_usage(user_id, "verse")
        await update.message.reply_text(await daily_verse_hadith(user_id), reply_markup=get_religious_keyboard()); return
    if text in ("🕌 مناسبت مذهبی", "مناسبت مذهبی"):
        track_usage(user_id, "rel_cd")
        # معماری مشابه تقویم: نمای کلی + مناسبت‌های نزدیک + نمای ماه جاری قمری
        body = religious_countdown()
        body += "\n\n" + "—" * 12 + "\n" + religious_month_view()
        await update.message.reply_text(body, reply_markup=get_religious_keyboard()); return
    if text in ("🙏 استخاره", "استخاره"):
        track_usage(user_id, "istikhara")
        context.user_data["waiting_for"] = "istikhara_confirm"
        await update.message.reply_text(istikhara_intro(), reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("🙏 استخاره بگیر")], [KeyboardButton("🔙 بازگشت به مذهبی")]],
            resize_keyboard=True
        )); return
    if text == "🙏 استخاره بگیر":
        context.user_data.pop("waiting_for", None)
        track_usage(user_id, "istikhara_do")
        await update.message.reply_text(await istikhara(user_id), reply_markup=get_religious_keyboard()); return
    if text == "🔙 بازگشت به مذهبی":
        context.user_data.pop("waiting_for", None)
        await update.message.reply_text("🕌 مذهبی:", reply_markup=get_religious_keyboard()); return
    if text in ("🔔 تنظیم اذان", "تنظیم اذان"):
        track_usage(user_id, "azan")
        await _show_azan_settings(update, user_id, city)
        return
    # دکمه‌های شخصی‌سازی اذان
    if text in ("🔔 اعلان‌ها: روشن", "🔕 اعلان‌ها: خاموش"):
        settings = get_azan_settings(user_id)
        set_azan_master(user_id, not settings["enabled"])
        await _show_azan_settings(update, user_id, city, note="وضعیت کلی اعلان‌ها تغییر کرد.")
        return
    if text in ("🔄 همه روشن",):
        set_azan_master(user_id, True)
        for key in ("fajr", "dhuhr", "asr", "maghrib", "isha"):
            field = f"notify_{key}"
            update_user_field(user_id, field, 1)
        await _show_azan_settings(update, user_id, city, note="همه اذان‌ها روشن شدند.")
        return
    if text in ("⏹ همه خاموش",):
        for key in ("fajr", "dhuhr", "asr", "maghrib", "isha"):
            update_user_field(user_id, f"notify_{key}", 0)
        await _show_azan_settings(update, user_id, city, note="همه اذان‌ها خاموش شدند.")
        return
    return False
