"""
مناسبت‌های مذهبی و قمری — معماری هم‌تراز با تقویم (bot/api/calendar.py + bot/utils/events.py)

از getterهای مشترک get_hijri_events استفاده می‌کند تا منبع حقیقت واحد باشد
و نمایش ساختاریافته (امروز / آینده نزدیک / ماه جاری) ارائه دهد.
"""
from __future__ import annotations
from bot.utils.modular_loader import load_modular_part

from datetime import datetime, timedelta
from typing import List, Tuple, Optional

try:
    import jdatetime
except ImportError:  # optional runtime fallback for stripped environments
    jdatetime = None
import pytz
try:
    from hijri_converter import Gregorian
except ImportError:  # optional dependency; functions degrade to empty/unknown dates
    Gregorian = None

from bot.config import config
from bot.utils.events import get_hijri_events

tehran_tz = pytz.timezone(config.TIMEZONE)

HIJRI_MONTH_NAMES = {
    1: "محرم", 2: "صفر", 3: "ربیع‌الاول", 4: "ربیع‌الثانی",
    5: "جمادی‌الاول", 6: "جمادی‌الثانی", 7: "رجب", 8: "شعبان",
    9: "رمضان", 10: "شوال", 11: "ذی‌قعده", 12: "ذی‌الحجه",
}


load_modular_part(__file__, 'events_parts/part_001__to_shamsi_str.py')


load_modular_part(__file__, 'events_parts/part_002__hijri_label.py')


load_modular_part(__file__, 'events_parts/part_003__events_for_gregorian.py')


load_modular_part(__file__, 'events_parts/part_004_get_today_religious_events.py')


load_modular_part(__file__, 'events_parts/part_005_get_upcoming_religious_events.py')


load_modular_part(__file__, 'events_parts/part_006_get_month_religious_events.py')


load_modular_part(__file__, 'events_parts/part_007_religious_countdown.py')


load_modular_part(__file__, 'events_parts/part_008_religious_month_view.py')
