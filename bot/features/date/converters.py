"""
مبدل تاریخ (شمسی ↔ میلادی ↔ قمری) و محاسبه سن دقیق
"""
from bot.utils.modular_loader import load_modular_part
import re
from datetime import datetime, date, timedelta
import jdatetime
from hijri_converter import Gregorian, Hijri
import pytz
from bot.config import config

tehran_tz = pytz.timezone(config.TIMEZONE)

HIJRI_MONTHS = {
    1: "محرم", 2: "صفر", 3: "ربیع‌الاول", 4: "ربیع‌الثانی",
    5: "جمادی‌الاول", 6: "جمادی‌الثانی", 7: "رجب", 8: "شعبان",
    9: "رمضان", 10: "شوال", 11: "ذی‌قعده", 12: "ذی‌الحجه"
}
HIJRI_MONTHS_REV = {v: k for k, v in HIJRI_MONTHS.items()}
# نام‌های رایج جایگزین
HIJRI_MONTHS_REV.update({
    "ربیع الاول": 3, "ربیع اول": 3,
    "ربیع الثانی": 4, "ربیع دوم": 4,
    "جمادی الاول": 5, "جمادی اول": 5,
    "جمادی الثانی": 6, "جمادی دوم": 6,
    "ذیقعده": 11, "ذی قعده": 11,
    "ذیالحجه": 12, "ذی الحجه": 12, "ذیحجه": 12,
})

PERSIAN_MONTHS = {
    1: "فروردین", 2: "اردیبهشت", 3: "خرداد", 4: "تیر",
    5: "مرداد", 6: "شهریور", 7: "مهر", 8: "آبان",
    9: "آذر", 10: "دی", 11: "بهمن", 12: "اسفند"
}
PERSIAN_MONTHS_REV = {v: k for k, v in PERSIAN_MONTHS.items()}

GREGORIAN_MONTHS = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December"
}


load_modular_part(__file__, 'converters_parts/part_001_to_persian_num.py')


load_modular_part(__file__, 'converters_parts/part_002__normalize.py')


load_modular_part(__file__, 'converters_parts/part_003_parse_date.py')


load_modular_part(__file__, 'converters_parts/part_004_convert_date.py')


load_modular_part(__file__, 'converters_parts/part_005__gregorian_to_hijri.py')


load_modular_part(__file__, 'converters_parts/part_006_calculate_age.py')


load_modular_part(__file__, 'converters_parts/part_007_parse_birth_datetime.py')


# ───────────────── برج فلکی ─────────────────

ZODIAC = [
    # (ماه شروع, روز شروع, ماه پایان, روز پایان, نام)
    (1, 1, 1, 20, "♑ بزغاله (جدی)"),
    (1, 21, 2, 19, "♒ دلو"),
    (2, 20, 3, 20, "♓ حوت"),
    (3, 21, 4, 20, "♈ حمل (فروردین)"),
    (4, 21, 5, 21, "♉ ثور"),
    (5, 22, 6, 21, "♊ جوزا"),
    (6, 22, 7, 22, "♋ سرطان"),
    (7, 23, 8, 22, "♌ اسد"),
    (8, 23, 9, 22, "♍ سنبله"),
    (9, 23, 10, 22, "♎ میزان"),
    (10, 23, 11, 21, "♏ عقرب"),
    (11, 22, 12, 21, "♐ قوس"),
    (12, 22, 12, 31, "♑ بزغاله (جدی)"),
]

# حیوان سال چینی/ایرانی (۱۲ ساله) — بر اساس سال شمسی
# سال ۱۳۴۸ = خروس ... مرجع رایج
CHINESE_ANIMALS = [
    "🐀 موش", "🐂 گاو", "🐅 ببر", "🐇 خرگوش",
    "🐉 اژدها", "🐍 مار", "🐎 اسب", "🐐 بز",
    "🐒 میمون", "🐓 خروس", "🐕 سگ", "🐖 خوک",
]


load_modular_part(__file__, 'converters_parts/part_008_get_zodiac.py')


load_modular_part(__file__, 'converters_parts/part_009_get_zodiac_from_shamsi.py')


load_modular_part(__file__, 'converters_parts/part_010_get_animal_year.py')


load_modular_part(__file__, 'converters_parts/part_011_zodiac_and_animal.py')


# ───────────────── روزشمار تولد ─────────────────

load_modular_part(__file__, 'converters_parts/part_012_birthday_countdown.py')


# ───────────────── سن قمری و سن تکلیف ─────────────────

load_modular_part(__file__, 'converters_parts/part_013_lunar_age.py')


# ───────────────── اختلاف دو تاریخ ─────────────────

load_modular_part(__file__, 'converters_parts/part_014_date_diff.py')


load_modular_part(__file__, 'converters_parts/part_015_parse_two_dates.py')
