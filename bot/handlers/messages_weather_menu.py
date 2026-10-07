"""Semantic message-routing handlers. Extracted from the legacy text handler without removing behavior."""
from .messages_common import *  # noqa: F401,F403
from . import messages_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})

async def handle_weather_menu(update, context, text, user_id, city=None, first_name=None):
    # هوا
    if text in ("🌤 پیش‌بینی هوا", "پیش‌بینی هوا"):
        track_usage(user_id, "forecast")
        await update.message.reply_text(await weather_forecast(city), reply_markup=get_weather_geo_keyboard()); return
    if text in ("🌫 کیفیت هوا", "کیفیت هوا"):
        track_usage(user_id, "aqi")
        await update.message.reply_text(await air_quality(city), reply_markup=get_weather_geo_keyboard()); return
    if text in ("🗺 فاصله شهرها", "فاصله شهرها", "🗺 فاصله جهانی", "فاصله جهانی"):
        context.user_data["waiting_for"] = "distance"; track_usage(user_id, "distance")
        await update.message.reply_text(
            "🗺 فاصله جهانی\n"
            "🌍 همه شهرها و کشورهای دنیا پشتیبانی می‌شود.\n\n"
            "دو مکان را بفرستید:\n"
            "• تهران مشهد\n"
            "• تهران تا ترکیه\n"
            "• ایران ژاپن\n"
            "• Paris to Tokyo\n"
            "• New York - Brazil",
            reply_markup=get_tools_keyboard(),
        ); return
    if text in ("📍 لوکیشن من", "لوکیشن من"):
        track_usage(user_id, "location")
        await update.message.reply_text(f"📍 لوکیشن را از 📎 بفرستید.\nشهر فعلی: {city}", reply_markup=get_weather_geo_keyboard()); return
    return False
