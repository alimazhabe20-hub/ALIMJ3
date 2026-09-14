from bot.utils.modular_loader import load_modular_part
from bot.utils.city_data import IRAN_CITIES, IRAQ_CITIES, CITY_COUNTRY, ALL_CITIES
from bot.utils.keyboard_factory import (
    get_refresh_button, get_main_keyboard, get_ai_keyboard, get_ai_model_keyboard,
    get_more_keyboard, get_date_tools_keyboard, get_religious_keyboard, get_market_keyboard,
    get_weather_geo_keyboard, get_tools_keyboard, get_azan_keyboard, get_fun_keyboard,
    get_joke_keyboard, get_profile_keyboard, get_smart_settings_keyboard, get_country_keyboard,
    get_iran_cities_keyboard, get_iraq_cities_keyboard, get_language_keyboard,
    get_font_keyboard, get_font_en_keyboard, get_font_fa_keyboard, get_gold_analysis_keyboard,
)
from telegram import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove,
)
import jdatetime
import pytz
from datetime import datetime
from bot.config import config
from bot.api.calendar import get_today_tehran, get_hijri_date, get_shamsi_events, get_hijri_events
from bot.api.prayer import get_prayer_times, get_next_prayer_time, get_prayer_times_for_date
from bot.api.weather import get_weather, format_weather
from bot.api.tgju import get_market_prices
from bot.utils.texts import get_text
from bot.utils.motivation import get_motivation
from bot.database import get_user_city, get_user_country, get_user_language

PERSIAN_MONTHS = {
    1: "فروردین", 2: "اردیبهشت", 3: "خرداد", 4: "تیر",
    5: "مرداد", 6: "شهریور", 7: "مهر", 8: "آبان",
    9: "آذر", 10: "دی", 11: "بهمن", 12: "اسفند"
}
PERSIAN_WEEKDAYS = {
    0: "شنبه", 1: "یکشنبه", 2: "دوشنبه", 3: "سه‌شنبه",
    4: "چهارشنبه", 5: "پنجشنبه", 6: "جمعه"
}

load_modular_part(__file__, 'helpers_parts/part_001_to_persian_num.py')





load_modular_part(__file__, 'helpers_parts/part_002_build_message.py')


load_modular_part(__file__, 'helpers_parts/part_003__build_message_inner.py')

# ───────────────── فقط بروزرسانی زیر پیام (اینلاین) ─────────────────


# ───────────────── بقیه دکمه‌ها پایین صفحه ─────────────────


































# ───────────────── تقویم (اینلاین) ─────────────────

load_modular_part(__file__, 'helpers_parts/part_004_get_calendar_buttons.py')


load_modular_part(__file__, 'helpers_parts/part_005_get_calendar_text.py')










# Compatibility facade contract: these are intentionally re-exported names used
# by legacy handlers. Keep this list stable when refactoring the implementation.
__all__ = [
    "build_message", "to_persian_num", "get_calendar_buttons", "get_calendar_text",
    "get_refresh_button", "get_main_keyboard", "get_ai_keyboard", "get_ai_model_keyboard",
    "get_more_keyboard", "get_date_tools_keyboard", "get_religious_keyboard",
    "get_market_keyboard", "get_weather_geo_keyboard", "get_tools_keyboard",
    "get_azan_keyboard", "get_fun_keyboard", "get_joke_keyboard", "get_profile_keyboard",
    "get_smart_settings_keyboard", "get_country_keyboard", "get_iran_cities_keyboard",
    "get_iraq_cities_keyboard", "get_language_keyboard", "get_font_keyboard",
    "get_font_en_keyboard", "get_font_fa_keyboard",
]
