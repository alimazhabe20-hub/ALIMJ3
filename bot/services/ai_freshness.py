"""Temporal routing for AI requests.

Classifies only requests whose answers are time-sensitive. Static/general questions
remain untouched; time-sensitive questions are routed to a live tool when one is
available. The current year/date always comes from the runtime clock.
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
    category: str
    reference_date: str
    reference_year: int


def _norm(text: str) -> str:
    return (text or "").strip().replace("ي", "ی").replace("ك", "ک")


# Explicit temporal language. Do NOT treat the word «جدید» by itself as live;
# it is only live when the subject is time-sensitive (movie/news/product/etc.).
_TIME_MARKERS = re.compile(
    r"(?:امروز|الان|همین\s*الان|فعلی|فعلاً|در\s*حال\s*حاضر|این\s*(?:روز|هفته|ماه|سال)|"
    r"امسال|سال\s*جاری|اخیراً|اخیر|تازه|جدیدترین|آخرین|به.?روز(?:ترین)?|تا\s*الان|"
    r"today|now|current|latest|recent|newest|live|real.?time|this\s+(?:week|month|year)|"
    r"\b202[0-9]\b|\b203[0-9]\b)", re.I,
)
_NEWS = re.compile(r"(?:خبر|اخبار|خبر\s*جدید|آخرین\s*خبر|چه\s*خبر|news|breaking|headline)", re.I)
_MARKET = re.compile(r"(?:قیمت|نرخ|بیت.?کوین|bitcoin|اتریوم|ethereum|تتر|usdt|کریپتو|رمزارز|طلا|xau|دلار|یورو|سکه|ارز|stock|سهام)", re.I)
_WEATHER = re.compile(r"(?:هوا|آب.?وهوا|دما|دمای|باران|برف|رطوبت|پیش.?بینی\s*هوا|weather|forecast|air quality)", re.I)
_PRODUCT = re.compile(r"(?:خرید|بخر|فروشگاه|فروشنده|قیمت.*(?:گوشی|آیفون|iphone|لپ.?تاپ|تلویزیون|کفش|محصول|کالا)|(?:گوشی|آیفون|iphone|لپ.?تاپ|تلویزیون|کفش|محصول|کالا).*(?:قیمت|خرید|موجودی)|قیمت\s*روز|لینک\s*خرید|ارزان.?ترین|موجودی|price.*product|buy|shop)", re.I)
_MOVIE = re.compile(r"(?:فیلم|سریال|movie|series|show|IMDb|imdb|سینما)", re.I)
_MOVIE_FRESH = re.compile(r"(?:فیلم|سریال|movie|series|show).*(?:جدید|تازه|امسال|این\s*(?:ماه|سال)|اخیر|جدیدترین|آخرین)|(?:جدیدترین|آخرین|تازه|جدید).*(?:فیلم|سریال|movie|series)", re.I)


def current_datetime() -> datetime:
    return datetime.now(timezone.utc)


def is_live_required(text: str) -> bool:
    q = _norm(text)
    if not q:
        return False
    # Subject-specific dynamic data.
    if _NEWS.search(q) or _MARKET.search(q) or _WEATHER.search(q) or _PRODUCT.search(q):
        return True
    # Movie/TV is live only when the user asks for current/new/recent info.
    if _MOVIE_FRESH.search(q):
        return True
    # Generic temporal language is live, but a normal static question is not.
    return bool(_TIME_MARKERS.search(q))


def classify(text: str) -> FreshnessDecision:
    q = _norm(text)
    now = current_datetime()
    date = now.date().isoformat()
    year = now.year
    if not q or not is_live_required(q):
        return FreshnessDecision(False, None, "static_or_general", "general", date, year)
    if _PRODUCT.search(q):
        return FreshnessDecision(True, "search_shopping", "product/shopping data can change", "shopping", date, year)
    if _WEATHER.search(q):
        return FreshnessDecision(True, None, "weather data changes continuously", "weather", date, year)
    if _MARKET.search(q):
        return FreshnessDecision(True, None, "market data changes continuously", "market", date, year)
    if _NEWS.search(q):
        return FreshnessDecision(True, "web_search", "news must be verified live", "news", date, year)
    if _MOVIE_FRESH.search(q):
        return FreshnessDecision(True, "hub_movie_tv_latest", "current movie/TV catalog is required", "movie_tv", date, year)
    return FreshnessDecision(True, "web_search", "time-sensitive information requires live verification", "general_live", date, year)


def today_utc() -> str:
    return current_datetime().date().isoformat()


def build_instruction(text: str) -> str:
    d = classify(text)
    if not d.required:
        return ""
    tool_line = f"ابزار اجباری برای این درخواست: {d.tool}." if d.tool else "ابتدا از ابزار زنده/مرتبط ثبت‌شده استفاده کن و نتیجه آن را مبنا قرار بده."
    return (
        "\n\n[LIVE DATA REQUIRED]\n"
        f"این سؤال زمان‌مند است ({d.reason}). {tool_line} "
        "قبل از پاسخ نهایی، داده زنده را بررسی کن. برای اطلاعات فعلی، قیمت، خبر، آب‌وهوا، "
        "موجودی و پیشنهادهای جدید از حافظه مدل به‌عنوان واقعیت امروز استفاده نکن. "
        "اگر ابزار زنده شکست خورد یا داده قابل تأیید نداد، صریحاً بگو اطلاعات فعلی قابل تأیید نیست "
        "و عدد/خبر/موجودی حدسی ارائه نکن. "
        f"تاریخ مرجع سیستم: {d.reference_date} UTC و سال جاری: {d.reference_year}. "
        "برای فیلم/سریال جدید، سال جاری را از همین تاریخ استخراج کن؛ هرگز سال ثابتی مثل 2024 را سال جاری فرض نکن."
    )
