"""Freshness routing for AI requests.

Requests whose answer can change with time must use a live tool before the model
is allowed to answer.  This module deliberately does not contain provider logic;
it only classifies the user request and supplies a safe instruction.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class FreshnessDecision:
    required: bool
    tool: str | None
    reason: str


_LIVE_MARKERS = re.compile(
    r"(?:امروز|الان|همین الان|فعلی|فعلاً|فعلیه|جدیدترین|آخرین|جدیدترین|به.?روز|به.?روزترین|روز|این روزها|2026|2027|latest|current|today|now|newest|recent|live|real.?time)",
    re.I,
)
_NEWS_MARKERS = re.compile(
    r"(?:خبر|اخبار|آخرین خبر|خبر جدید|چه خبر|news|breaking|headline)", re.I
)
_PRODUCT_MARKERS = re.compile(
    r"(?:خرید|بخر|فروشگاه|فروشنده|قیمت.*(?:گوشی|آیفون|iphone|لپ.?تاپ|تلویزیون|کفش|خمیر|محصول|کالا)|"
    r"(?:گوشی|آیفون|iphone|لپ.?تاپ|تلویزیون|کفش|خمیر|محصول|کالا).*(?:قیمت|خرید|موجودی)|"
    r"قیمت روز محصول|لینک خرید|ارزان.?ترین|موجودی|price.*product|buy|shop)",
    re.I,
)
_MARKET_MARKERS = re.compile(
    r"(?:بیت.?کوین|bitcoin|اتریوم|ethereum|تتر|usdt|کریپتو|رمزارز|طلا|xau|دلار|یورو|سکه|ارز|"
    r"قیمت.*(?:دلار|یورو|طلا|سکه|بیت|اتریوم|تتر)|نرخ.*(?:دلار|یورو|ارز))",
    re.I,
)
_WEATHER_MARKERS = re.compile(
    r"(?:هوا|آب.?وهوا|دمای|باران|برف|رطوبت|weather|forecast|air quality|کیفیت هوا)", re.I
)
# Cover common Persian phrasings including «تاریخ الان» / «الان تاریخ»
_DATETIME_MARKERS = re.compile(
    r"(?:"
    r"تاریخ\s*(?:دقیق|فعلی|الان|امروز|چند|چیه|چیه\؟?)?|"
    r"امروز\s*(?:چندمه|چه\s*روز|چه\s*تاریخی|تاریخ)|"
    r"الان\s*(?:چه\s*)?(?:تاریخ|ساعت|چه\s*ساعتی|چند)|"
    r"ساعت\s*(?:الان|چنده|چند)|"
    r"(?:فردا|دیروز|پس\s*فردا)\s*(?:چندمه|تاریخ|چه\s*روز)|"
    r"current\s*(?:date|time|datetime)|"
    r"today(?:\s*date)?|tomorrow|yesterday|"
    r"what\s*(?:time|date)\s*is\s*it|right\s*now"
    r")",
    re.I,
)
_MOVIE_MARKERS = re.compile(
    r"(?:فیلم|سریال|movie|series|IMDb|فیلم\s*(?:جدید|تازه|امسال|این ماه|اخیر)|جدیدترین\s*(?:فیلم|سریال)|آخرین\s*(?:فیلم|سریال))", re.I
)


def is_live_required(text: str) -> bool:
    """Return True when answering from model memory would be unsafe/stale."""
    q = (text or "").strip()
    if not q:
        return False
    return bool(
        _DATETIME_MARKERS.search(q)
        or _LIVE_MARKERS.search(q)
        or _NEWS_MARKERS.search(q)
        or _PRODUCT_MARKERS.search(q)
        or _MARKET_MARKERS.search(q)
        or _WEATHER_MARKERS.search(q)
        or _MOVIE_MARKERS.search(q)
    )


def classify(text: str) -> FreshnessDecision:
    q = (text or "").strip()
    if not is_live_required(q):
        return FreshnessDecision(False, None, "static_or_general")
    if _DATETIME_MARKERS.search(q):
        return FreshnessDecision(
            True,
            "get_current_datetime",
            "current date/time must come from the real system clock",
        )
    if _PRODUCT_MARKERS.search(q):
        return FreshnessDecision(True, "search_shopping", "product/shopping data can change")
    if _MARKET_MARKERS.search(q):
        return FreshnessDecision(True, None, "market data can change")
    if _WEATHER_MARKERS.search(q):
        return FreshnessDecision(True, None, "weather data can change")
    if _MOVIE_MARKERS.search(q):
        return FreshnessDecision(
            True,
            "hub_movie_tv_latest",
            "movie/TV recommendations must use current catalog data",
        )
    return FreshnessDecision(True, "web_search", "time-sensitive information requires live verification")


def today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _live_clock_snapshot() -> str:
    """Best-effort real clock text for datetime questions (never invent)."""
    try:
        from bot.services.current_datetime import current_datetime

        return current_datetime("")
    except Exception as exc:
        # Absolute fallback so the model still sees a real system timestamp.
        now = datetime.now(timezone.utc)
        return (
            f"UTC fallback clock: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC "
            f"(tool error: {type(exc).__name__})"
        )


def build_instruction(text: str) -> str:
    decision = classify(text)
    if not decision.required:
        return ""
    tool_line = (
        f"ابزار اجباری برای این درخواست: {decision.tool}."
        if decision.tool
        else "ابتدا از ابزار زنده/مرتبط ثبت‌شده استفاده کن و نتیجه آن را مبنا قرار بده."
    )
    parts = [
        "\n\n[LIVE DATA REQUIRED]\n"
        f"این سؤال زمان‌مند است ({decision.reason}). {tool_line} "
        "قبل از پاسخ نهایی، داده زنده را بررسی کن. از دانش قدیمی مدل برای قیمت، خبر، "
        "موجودی، وضعیت فعلی یا مشخصات عرضه‌شده به‌عنوان واقعیت امروز استفاده نکن. "
        "اگر ابزار زنده شکست خورد یا داده قابل تأیید نداد، صریحاً بگو اطلاعات فعلی قابل تأیید نیست "
        "و هیچ عدد/خبر/موجودی/تاریخ حدسی ارائه نکن.\n"
        f"تاریخ مرجع سیستم: {today_utc()} (UTC). "
        "برای فیلم/سریال جدید، سال فعلی را از تاریخ مرجع استخراج کن و هرگز سال ثابتی مثل 2024 را سال جاری فرض نکن. "
        "نتایج را بر اساس سال فعلی و سپس سال قبل مرتب کن."
    ]

    # For pure date/time questions, also embed the real system clock so even if
    # the tool-calling path fails, the model still has ground-truth text and
    # must not invent Jalali/Gregorian dates from training memory.
    if decision.tool == "get_current_datetime":
        clock = _live_clock_snapshot()
        parts.append(
            "\n[SYSTEM CLOCK — SOURCE OF TRUTH]\n"
            f"{clock}\n"
            "پاسخ تاریخ/ساعت را فقط بر اساس بلوک بالا بنویس. "
            "هیچ تاریخ شمسی یا میلادی دیگری از حافظه مدل نساز و اعداد را عوض نکن."
        )
    return "".join(parts)
