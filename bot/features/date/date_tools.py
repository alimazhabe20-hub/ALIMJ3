"""
تاریخ و زمان — همه ابزارها (۱ تا ۱۰ + شمارش‌معکوس سفارشی)
"""
from bot.utils.modular_loader import load_modular_part
import re
from datetime import datetime, date, timedelta
import jdatetime
from hijri_converter import Gregorian, Hijri
import pytz
from bot.config import config
from bot.utils.events import shamsi_events, hijri_events

tehran_tz = pytz.timezone(config.TIMEZONE)

PERSIAN_MONTHS = {
    1: "فروردین", 2: "اردیبهشت", 3: "خرداد", 4: "تیر",
    5: "مرداد", 6: "شهریور", 7: "مهر", 8: "آبان",
    9: "آذر", 10: "دی", 11: "بهمن", 12: "اسفند"
}
PERSIAN_MONTHS_REV = {v: k for k, v in PERSIAN_MONTHS.items()}
PERSIAN_WEEKDAYS = {
    0: "شنبه", 1: "یکشنبه", 2: "دوشنبه", 3: "سه‌شنبه",
    4: "چهارشنبه", 5: "پنجشنبه", 6: "جمعه"
}
GREGORIAN_MONTHS = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December"
}
HIJRI_MONTHS = {
    1: "محرم", 2: "صفر", 3: "ربیع‌الاول", 4: "ربیع‌الثانی",
    5: "جمادی‌الاول", 6: "جمادی‌الثانی", 7: "رجب", 8: "شعبان",
    9: "رمضان", 10: "شوال", 11: "ذی‌قعده", 12: "ذی‌الحجه"
}
HIJRI_MONTHS_REV = {v: k for k, v in HIJRI_MONTHS.items()}
HIJRI_MONTHS_REV.update({
    "ربیع الاول": 3, "ربیع اول": 3, "ربیع الثانی": 4, "ربیع دوم": 4,
    "جمادی الاول": 5, "جمادی اول": 5, "جمادی الثانی": 6, "جمادی دوم": 6,
    "ذیقعده": 11, "ذی قعده": 11, "ذیالحجه": 12, "ذی الحجه": 12, "ذیحجه": 12,
})

ZODIAC = [
    (1, 1, 1, 20, "♑ بزغاله (جدی)"), (1, 21, 2, 19, "♒ دلو"),
    (2, 20, 3, 20, "♓ حوت"), (3, 21, 4, 20, "♈ حمل"),
    (4, 21, 5, 21, "♉ ثور"), (5, 22, 6, 21, "♊ جوزا"),
    (6, 22, 7, 22, "♋ سرطان"), (7, 23, 8, 22, "♌ اسد"),
    (8, 23, 9, 22, "♍ سنبله"), (9, 23, 10, 22, "♎ میزان"),
    (10, 23, 11, 21, "♏ عقرب"), (11, 22, 12, 21, "♐ قوس"),
    (12, 22, 12, 31, "♑ بزغاله (جدی)"),
]
CHINESE_ANIMALS = [
    "🐀 موش", "🐂 گاو", "🐅 ببر", "🐇 خرگوش", "🐉 اژدها", "🐍 مار",
    "🐎 اسب", "🐐 بز", "🐒 میمون", "🐓 خروس", "🐕 سگ", "🐖 خوک",
]

WORLD_CITIES = {
    "تهران": "Asia/Tehran", "دبی": "Asia/Dubai", "استانبول": "Europe/Istanbul",
    "لندن": "Europe/London", "پاریس": "Europe/Paris", "نیویورک": "America/New_York",
    "لس‌آنجلس": "America/Los_Angeles", "توکیو": "Asia/Tokyo", "پکن": "Asia/Shanghai",
    "مسکو": "Europe/Moscow", "سیدنی": "Australia/Sydney", "ریاض": "Asia/Riyadh",
}


load_modular_part(__file__, 'date_tools_parts/part_001_pn.py')


load_modular_part(__file__, 'date_tools_parts/part_002__norm.py')


load_modular_part(__file__, 'date_tools_parts/part_003_parse_shamsi.py')


load_modular_part(__file__, 'date_tools_parts/part_004_parse_any_date.py')


load_modular_part(__file__, 'date_tools_parts/part_005__g2h.py')


# ── ۱. روزشمار تولد ──
load_modular_part(__file__, 'date_tools_parts/part_006_birthday_countdown.py')


# ── ۲. برج + حیوان ──
load_modular_part(__file__, 'date_tools_parts/part_007_zodiac_animal.py')


# ── ۳. سن قمری + تکلیف ──
load_modular_part(__file__, 'date_tools_parts/part_008_lunar_age.py')


# ── ۴. اختلاف دو تاریخ (پیشرفته) ──
load_modular_part(__file__, 'date_tools_parts/part_009__days_in_jmonth.py')


load_modular_part(__file__, 'date_tools_parts/part_010__ymd_diff.py')


load_modular_part(__file__, 'date_tools_parts/part_011__g2h_safe.py')


load_modular_part(__file__, 'date_tools_parts/part_012_date_diff.py')


load_modular_part(__file__, 'date_tools_parts/part_013_parse_two_dates.py')


# ── ۵. اختلاف سن دو نفر (پیشرفته) ──
load_modular_part(__file__, 'date_tools_parts/part_014_age_diff.py')


# ── ۶. تبدیل تاریخ با روز هفته ──
load_modular_part(__file__, 'date_tools_parts/part_015_convert_with_weekday.py')


# ── ۷. تقویم ماه کامل ──
load_modular_part(__file__, 'date_tools_parts/part_016_month_calendar.py')


# ── ۸. مناسبت‌یاب ──
load_modular_part(__file__, 'date_tools_parts/part_017_search_events.py')


# ── ۹. شمارش‌معکوس نوروز ──
load_modular_part(__file__, 'date_tools_parts/part_018_nowruz_countdown.py')


# ── ۱۰. ساعت جهانی ──
load_modular_part(__file__, 'date_tools_parts/part_019_world_clock.py')


# ── شمارش‌معکوس سفارشی ──
load_modular_part(__file__, 'date_tools_parts/part_020_custom_countdown.py')


load_modular_part(__file__, 'date_tools_parts/part_021_parse_countdown.py')
