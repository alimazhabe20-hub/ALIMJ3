"""Semantic message-routing handlers. Extracted from the legacy text handler without removing behavior."""
from .messages_common import *  # noqa: F401,F403
from . import messages_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})

async def handle_date_menu(update, context, text, user_id, city=None, first_name=None):
    # تاریخ و سن
    if text in ("🔄 مبدل تاریخ", "مبدل تاریخ"):
        context.user_data["waiting_for"] = "date_convert"; track_usage(user_id, "date_convert")
        await update.message.reply_text("🔄 تاریخ:\n`1403/05/18` یا `2024/08/09`", reply_markup=get_date_tools_keyboard()); return
    if text in ("🎂 محاسبه سن", "🎂 محاسبه سن دقیق", "محاسبه سن"):
        context.user_data["waiting_for"] = "age_calc"; track_usage(user_id, "age_calc")
        await update.message.reply_text("🎂 تولد شمسی:\n`1375/03/15`", reply_markup=get_date_tools_keyboard()); return
    if text in ("🎉 روزشمار تولد", "روزشمار تولد"):
        context.user_data["waiting_for"] = "birthday"; track_usage(user_id, "birthday")
        bd = get_birth_date(user_id)
        if bd and len(bd.split("/")) == 3:
            p = bd.split("/"); context.user_data.pop("waiting_for", None)
            await update.message.reply_text(birthday_countdown(int(p[0]), int(p[1]), int(p[2])), reply_markup=get_date_tools_keyboard()); return
        await update.message.reply_text("🎉 تولد شمسی:\n`1375/03/15`", reply_markup=get_date_tools_keyboard()); return
    if text in ("♈ برج و حیوان", "برج و حیوان"):
        context.user_data["waiting_for"] = "zodiac"; track_usage(user_id, "zodiac")
        await update.message.reply_text("♈ تولد شمسی:\n`1375/03/15`", reply_markup=get_date_tools_keyboard()); return
    if text in ("🌙 سن قمری", "سن قمری"):
        context.user_data["waiting_for"] = "lunar"; track_usage(user_id, "lunar")
        await update.message.reply_text("🌙 تولد شمسی:\n`1375/03/15`", reply_markup=get_date_tools_keyboard()); return
    if text in ("📆 اختلاف تاریخ", "📆 اختلاف دو تاریخ", "اختلاف تاریخ"):
        context.user_data["waiting_for"] = "date_diff"; track_usage(user_id, "date_diff")
        await update.message.reply_text(
            "📆 دو تاریخ شمسی بفرست:\n"
            "`1375/03/15 1403/05/18`\n\n"
            "خروجی: سال/ماه/روز • هفته • ساعت • روز کاری • میلادی و قمری",
            reply_markup=get_date_tools_keyboard(),
        ); return
    if text in ("👥 اختلاف سن", "اختلاف سن"):
        context.user_data["waiting_for"] = "age_diff"; track_usage(user_id, "age_diff")
        await update.message.reply_text(
            "👥 دو تاریخ تولد شمسی بفرست:\n"
            "`1375/03/15 1380/06/20`\n\n"
            "خروجی: سن هر نفر • اختلاف دقیق • سن قمری • نسبت سنی",
            reply_markup=get_date_tools_keyboard(),
        ); return
    if text in ("📅 تقویم ماه", "تقویم ماه"):
        track_usage(user_id, "month_cal")
        await update.message.reply_text(month_calendar(), reply_markup=get_date_tools_keyboard()); return
    if text in ("🔍 مناسبت‌یاب", "مناسبت‌یاب"):
        context.user_data["waiting_for"] = "event_search"; track_usage(user_id, "event_search")
        await update.message.reply_text("🔍 کلمه کلیدی:\n`نوروز`", reply_markup=get_date_tools_keyboard()); return
    if text in ("🌸 شمارش نوروز", "شمارش نوروز"):
        track_usage(user_id, "nowruz")
        await update.message.reply_text(nowruz_countdown(), reply_markup=get_date_tools_keyboard()); return
    if text in ("🌍 ساعت جهانی", "ساعت جهانی"):
        track_usage(user_id, "world_clock")
        await update.message.reply_text(world_clock(), reply_markup=get_date_tools_keyboard()); return
    if text in ("⏳ شمارش‌معکوس", "شمارش‌معکوس"):
        context.user_data["waiting_for"] = "countdown"; track_usage(user_id, "countdown")
        await update.message.reply_text("⏳ تاریخ:\n`1405/01/01 نوروز`", reply_markup=get_date_tools_keyboard()); return
    return False
