"""Semantic message-routing handlers. Extracted from the legacy text handler without removing behavior."""
from .messages_common import *  # noqa: F401,F403
from . import messages_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})

def _is_back(text):
    t = text.strip()
    return t in ("🔙 بازگشت", "بازگشت") or "بازگشت" in t

def _is_back_more(text):
    return "بازگشت به بیشتر" in text

async def handle_basic_menu(update, context, text, user_id, city=None, first_name=None):
    if text in ("🏙 انتخاب شهر", "انتخاب شهر"):
        await update.message.reply_text("🏙 کشور:", reply_markup=get_country_keyboard()); return
    if text in ("📅 تقویم", "تقویم"):
        t = get_today_tehran()
        await update.message.reply_text(get_calendar_text(t.year, t.month, t.day, user_id), reply_markup=get_calendar_buttons(t.year, t.month, t.day, user_id)); return
    if text in ("🌍 زبان", "زبان"):
        await update.message.reply_text("🌍 زبان:", reply_markup=get_language_keyboard()); return
    if text in ("➕ بیشتر", "بیشتر"):
        await update.message.reply_text("➕ بخش را انتخاب کنید:", reply_markup=get_more_keyboard()); return
    if text in ("📥 دانلودر فایل", "دانلودر فایل", "دانلودر"):
        from bot.handlers.v71_handlers import downloader_entry_v71
        await downloader_entry_v71(update, context)
        return
    if text == "🤖 دستیار هوشمند":
        providers = enabled_providers()
        context.user_data["ai_mode"] = True
        provider_text = "، ".join(providers) if providers else "هیچ سرویس فعالی ندارد"
        await update.message.reply_text(
            "🤖 دستیار هوشمند روز زیبا\n\n"
            "پیامت را بفرست تا به هوش مصنوعی ارسال شود.\n"
            f"سرویس‌های فعال: {provider_text}",
            reply_markup=get_ai_keyboard(user_id),
        )
        return
    if text == "📅 تاریخ و سن":
        await update.message.reply_text("📅 تاریخ و سن:", reply_markup=get_date_tools_keyboard()); return
    if text == "🕌 مذهبی":
        await update.message.reply_text("🕌 مذهبی:", reply_markup=get_religious_keyboard()); return
    if text == "💰 بازار":
        await update.message.reply_text("💰 بازار:", reply_markup=get_market_keyboard()); return
    if text == "🌤 هوا و مکان":
        await update.message.reply_text("🌤 هوا و مکان:", reply_markup=get_weather_geo_keyboard()); return
    if text == "🛠 ابزارها":
        await update.message.reply_text("🛠 ابزارها:", reply_markup=get_tools_keyboard()); return
    if text == "🎮 سرگرمی":
        await update.message.reply_text("🎮 سرگرمی:", reply_markup=get_fun_keyboard()); return
    if text in ("🎨 فونت", "فونت"):
        await update.message.reply_text("🎨 بخش فونت:", reply_markup=get_font_keyboard()); return
    if text in ("📋 لیست فونت‌ها", "📋 لیست همه فونت‌ها"):
        await update.message.reply_text(list_fonts(), reply_markup=get_font_keyboard()); return
    if text == "🇬🇧 فونت انگلیسی":
        await update.message.reply_text("🇬🇧 یک فونت انگلیسی انتخاب کنید:", reply_markup=get_font_en_keyboard()); return
    if text == "🇮🇷 فونت فارسی":
        await update.message.reply_text("🇮🇷 یک فونت فارسی/تزئینی انتخاب کنید:", reply_markup=get_font_fa_keyboard()); return
    if text == "🌈 همه فونت‌ها":
        context.user_data["waiting_for"] = "font_all"
        await update.message.reply_text("🌈 یک کلمه یا جمله بفرستید تا روی همه فونت‌ها اعمال شود:", reply_markup=get_font_keyboard()); return
    if text == "🔙 بازگشت فونت":
        await update.message.reply_text("🎨 بخش فونت:", reply_markup=get_font_keyboard()); return
    # انتخاب فونت از نام نمایشی
    name_to_key = {v: k for k, v in FONT_NAMES.items()}
    name_to_key.update({v[:18]: k for k, v in FONT_NAMES.items()})
    if text in name_to_key or text in FONT_NAMES:
        key = name_to_key.get(text, text)
        context.user_data["selected_font"] = key
        context.user_data["waiting_for"] = "font_text"
        await update.message.reply_text(f"🎨 فونت انتخاب شد.\nمتن را بفرستید:", reply_markup=get_font_keyboard()); return
    if text == "👤 پروفایل":
        await update.message.reply_text("👤 پروفایل:", reply_markup=get_profile_keyboard()); return
    if _is_back_more(text):
        await update.message.reply_text("➕ منوی بیشتر:", reply_markup=get_more_keyboard()); return
    return False
