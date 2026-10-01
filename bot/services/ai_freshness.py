"""Freshness policy for Rooze Ziba AI.

Decides when an answer must be grounded in a live web search instead of
relying on the model's training knowledge. This module intentionally stays
small so freshness policy can evolve without touching provider code.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone


# Explicit freshness words cover Persian, English, and common user shorthand.
_EXPLICIT = re.compile(
    r"(?:"
    r"امروز|امشب|الان|اکنون|فعلی|لحظه.?ای|همین.?الان|جدیدترین|آخرین|تازه|جدید|به.?روز|بروز|روز.?آمد|"
    r"خبر|اخبار|آپدیت|به.?روزرسانی|نسخه.?جدید|عرضه|معرفی|منتشر|موجودی|در.?دسترس|قیمت|نرخ|ارزش|"
    r"today|tonight|now|right\s*now|current|latest|newest|recent|fresh|live|real.?time|"
    r"news|price|rate|value|release|released|launch|launched|available|availability|stock|update|version"
    r")",
    re.I,
)

# Requests about products/services are frequently time-sensitive even when the
# user does not explicitly say "latest". The model must verify these online.
_PRODUCT = re.compile(
    r"(?:"
    r"آیفون|ایفون|اپل|سامسونگ|شیائومی|پوکو|وان.?پلاس|گوگل.?پیکسل|هواوی|لپ.?تاپ|گوشی|موبایل|"
    r"iphone|ipad|macbook|apple|samsung|xiaomi|poco|oneplus|pixel|huawei|laptop|phone|gpu|cpu|"
    r"کارت.?گرافیک|پردازنده|کنسول|پلی.?استیشن|ایکس.?باکس|ps[45]|xbox|"
    r"محصول|کالا|فروشگاه|خرید|فروش|قیمت.?فروش|ارزان|گران|موجودی|"
    r"product|shopping|shop|buy|sell|store"
    r")",
    re.I,
)

# Market/financial data is always live-sensitive.
_MARKET = re.compile(
    r"(?:"
    r"بیت.?کوین|اتریوم|کریپتو|رمزارز|ارز دیجیتال|دلار|یورو|پوند|طلا|سکه|بورس|سهام|بازار|"
    r"bitcoin|btc|ethereum|eth|crypto|forex|gold|silver|stock|stocks|market|usd|eur|gbp|"
    r"نفت|oil|nasdaq|s&p|dow\s*jones"
    r")",
    re.I,
)


def requires_live_shopping(query: str) -> bool:
    """Return True when the request is asking for live product/marketplace data."""
    text = (query or "").strip()
    if not text:
        return False
    return bool(re.search(
        r"(?:قیمت|چنده|چند\s*هزار|چند\s*تومنه|خرید|فروشگاه|فروشنده|لینک\s*خرید|ارزان.?ترین|موجودی|تخفیف|\bprice\b|\bbuy\b|\bshop\b|\bstore\b|\bstock\b|\bavailable\b)",
        text, re.I,
    ) and _PRODUCT.search(text))


def requires_live_web(query: str) -> bool:
    """Return True when the user's request should be answered from live web data."""
    text = (query or "").strip()
    if not text:
        return False
    if _EXPLICIT.search(text) or _PRODUCT.search(text) or _MARKET.search(text):
        return True

    # A product/model question such as "iphone 18 pro max چند؟" may contain no
    # explicit freshness word. Product-looking text with a model number should
    # still be verified online.
    if re.search(r"(?:iphone|آیفون|ایفون|galaxy|گلکسی|pixel|پیکسل|macbook|ps\s*[45]|xbox)\s*[-\w]*\d", text, re.I):
        return True
    return False


def freshness_query(query: str) -> str:
    """Add today's UTC date to live searches so results are time-aware."""
    day = datetime.now(timezone.utc).date().isoformat()
    return f"{query.strip()} latest current information {day}".strip()
