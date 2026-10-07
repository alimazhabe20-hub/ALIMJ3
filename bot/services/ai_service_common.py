"""Shared imports and module state for the refactored ai_service."""

from __future__ import annotations

"""Ordered compatibility loader for cleaned source chunks."""

"""AI router, per-user model selection, and multi-key rotation for Rooze Ziba."""

import asyncio

import base64

import os

import time

from collections import defaultdict, deque

from typing import Deque, Dict, List, Optional, Tuple

import httpx

from bot.logger import logger

SYSTEM_PROMPT = os.getenv(
    "AI_SYSTEM_PROMPT",
    "تو دستیار هوشمند ربات «روز زیبا» هستی و به قابلیت‌های واقعی همین ربات دسترسی داری. "
    "با لحنی گرم، طبیعی، محترمانه و کمی شوخ‌طبع (فقط وقتی فضا مناسب است) فارسی روان صحبت کن. "
    "اگر کاربر به زبان دیگری پیام داد، دقیقاً به همان زبان پاسخ بده. "
    "پاسخ‌هایت باید کامل، مفصل و جامع باشد. هرگز جواب را خلاصه نکن مگر اینکه کاربر صریحاً بگوید «خلاصه بگو» یا «کوتاه». "
    "وقتی کاربر درباره آب‌وهوا، اوقات شرعی، قیمت ارز/طلا/کریپتو، تبدیل تاریخ، سن، قبله، اذکار، آیه و حدیث، "
    "ساعت جهانی یا فاصله شهرها می‌پرسد، از ابزارهای ربات استفاده کن یا از «دادهٔ زنده» که در پیام آمده استفاده کن؛ "
    "هرگز عدد و قیمت ساختگی نگو. "
    "اگر داده زنده در اختیار داری، همان را مبنا قرار بده و واضح جواب بده. "
    "از حاشیه‌روی بی‌ربط پرهیز کن. هدف تو این است که کاربر حس کند دستیار ربات واقعاً به همه قابلیت‌های ربات وصل است. "
    "وقتی کاربر درباره ارزهای دیجیتال، نمودار قیمت یا تحلیل کریپتو می‌پرسد، از ابزار get_crypto_analysis_data برای دریافت دادهٔ زنده استفاده کن؛ CoinGlass فقط وقتی کلید آن روی سرور تنظیم شده باشد دادهٔ مشتقه می‌دهد. "
    "هرگز از روی حدس، قیمت یا شاخص بازار نساز و حتماً منبع داده و غیرقطعی بودن تحلیل را روشن کن. "
    "این ربات می‌تواند جواب را با ویس (صدا) برای کاربر بفرستد. "
    "هرگز نگو که نمی‌توانی فایل صوتی بفرستی یا کاربر را به اپ دیگر ارجاع نده. "
    "اگر کاربر فقط گفت «ویس بفرست» یا «با صدا»، یک تأیید کوتاه بده مثل «حتماً، الان با ویس می‌فرستم.» — خود سیستم ویس را می‌فرستد.",
)

MAX_INPUT = int(os.getenv("AI_MAX_INPUT", "6000"))

MAX_OUTPUT = int(os.getenv("AI_MAX_OUTPUT", "2800"))

HISTORY_ITEMS = max(2, int(os.getenv("AI_HISTORY_ITEMS", "8")))

TIMEOUT = float(os.getenv("AI_TIMEOUT", "40"))

KEY_COOLDOWN_SEC = int(os.getenv("AI_KEY_COOLDOWN_SEC", str(12 * 3600)))

KEY_SHORT_COOLDOWN_SEC = int(os.getenv("AI_KEY_SHORT_COOLDOWN_SEC", "90"))

_DEFAULT_ORDER = [
    x.strip().lower()
    for x in os.getenv(
        "AI_DEFAULT_ORDER",
        # groq اول چون مدل‌های instant خیلی سریع‌اند
        "groq,gemini,cerebras,cloudflare,openrouter",
    ).split(",")
    if x.strip()
]

_HISTORY: Dict[int, Deque[Tuple[str, str]]] = defaultdict(
    lambda: deque(maxlen=HISTORY_ITEMS)
)

_LOCKS: Dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

_USER_SELECTION: Dict[int, Tuple[str, str]] = {}

_SUMMARY_RUNNING: set[int] = set()

_HTTP: Optional[httpx.AsyncClient] = None

import os

from bot.services.ai_runtime import (
    clear_history,
    available_providers,
    set_selected_provider,
    get_selected_model,
)
