"""
قابلیت‌های اضافه دستیار: نمودار، جستجوی وب، کش جواب برای دکمه ویس،
یادآوری زبان‌طبیعی، OCR فیش، و کمک‌کننده‌های استریم.
"""
from __future__ import annotations
from bot.utils.modular_loader import load_modular_part

import io
import re
import time
import hashlib
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta

import pytz

from bot.logger import logger

TEHRAN = pytz.timezone("Asia/Tehran")

# answer_id -> (user_id, text, expires, prompt)
_ANSWER_CACHE: Dict[str, Tuple[int, str, float, str]] = {}
_CACHE_TTL = 3600 * 6

_LAST_ANSWER: Dict[int, str] = {}
# user_id -> last original user prompt (for continue)
_LAST_PROMPT: Dict[int, str] = {}
# user_id -> last answer_id
_LAST_ANSWER_ID: Dict[int, str] = {}


load_modular_part(__file__, 'ai_extras_parts/part_001_parse_natural_weather.py')


load_modular_part(__file__, 'ai_extras_parts/part_002_parse_natural_crypto_price.py')


load_modular_part(__file__, 'ai_extras_parts/part_003_store_answer.py')


load_modular_part(__file__, 'ai_extras_parts/part_004_get_stored_answer.py')


load_modular_part(__file__, 'ai_extras_parts/part_005_get_stored_prompt.py')


load_modular_part(__file__, 'ai_extras_parts/part_006_get_last_answer.py')


load_modular_part(__file__, 'ai_extras_parts/part_007_get_last_prompt.py')


load_modular_part(__file__, 'ai_extras_parts/part_008_get_last_answer_id.py')


# ── نمودار ──────────────────────────────────────────────────────────────────

load_modular_part(__file__, 'ai_extras_parts/part_009_make_chart_image.py')


load_modular_part(__file__, 'ai_extras_parts/part_010_parse_chart_request.py')


# ── جستجوی وب ───────────────────────────────────────────────────────────────

load_modular_part(__file__, 'ai_extras_parts/part_011_web_search.py')


# ── یادآوری زبان طبیعی ─────────────────────────────────────────────────────

load_modular_part(__file__, 'ai_extras_parts/part_012_parse_natural_reminder.py')


# ── OCR فیش (پرامپت تقویت‌شده) ─────────────────────────────────────────────

RECEIPT_OCR_PROMPT = (
    "این تصویر احتمالاً فیش، رسید، فاکتور یا کارت است. "
    "همه متن را با دقت OCR کن و ساخت‌یافته به فارسی برگردان:\n"
    "• فروشنده / فروشگاه\n"
    "• تاریخ و ساعت\n"
    "• اقلام (نام + تعداد + قیمت)\n"
    "• جمع کل / مالیات / تخفیف\n"
    "• شماره پیگیری / مرجع\n"
    "• هر مبلغ یا شماره مهم دیگر\n"
    "اگر خوانا نبود بگو کدام بخش مبهم است. اعداد را دقیق بنویس."
)


load_modular_part(__file__, 'ai_extras_parts/part_013_enhance_ocr_prompt.py')


# ── کیبورد اینلاین زیر جواب AI ───────────────────────────────────────────────

load_modular_part(__file__, 'ai_extras_parts/part_014_get_ai_result_keyboard.py')


load_modular_part(__file__, 'ai_extras_parts/part_015_build_continue_prompt.py')


