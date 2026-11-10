"""تشخیص هوشمند نیت پیام گروه."""
from __future__ import annotations

import re
from typing import Optional, Tuple


def detect_intent(text: str) -> Tuple[Optional[str], str]:
    """
    Returns (intent, cleaned_query)

    intents:
      help, download, price_dollar, price_euro, price_gold, crypto,
      analyze_gold, analyze_crypto, weather, shop, vision, ai
    """
    t = (text or "").strip()
    if not t:
        return "help", ""

    low = t.lower()
    cleaned = re.sub(r"^(?:ربات|هوشمند|!)\s*", "", t, flags=re.I).strip()
    cleaned = re.sub(r"^/(?:ask|ai)(?:@\w+)?\s*", "", cleaned, flags=re.I).strip() or cleaned

    if cleaned in {"ربات", "هوشمند", "!", "bot", "help", "راهنما"} or re.fullmatch(r"ربات\s*", t):
        return "help", cleaned

    if re.search(r"https?://|www\.", t, re.I) and re.search(
        r"(instagram|tiktok|facebook|twitter|x\.com|youtube|youtu\.be|vimeo)", t, re.I
    ):
        return "download", cleaned

    # تحلیل بازار — قبل از vision
    if re.search(r"تحلیل\s*طلا|طلا\s*را?\s*تحلیل|analyze\s*gold", t, re.I):
        return "analyze_gold", cleaned
    if re.search(
        r"تحلیل\s*(?:بیتکوین|بیت‌کوین|اتریوم|کریپتو|btc|eth)|(?:بیتکوین|btc)\s*را?\s*تحلیل",
        t,
        re.I,
    ):
        return "analyze_crypto", cleaned

    if re.search(r"قیمت\s*دلار|دلار\s*چند|نرخ\s*دلار", t, re.I):
        return "price_dollar", cleaned
    if re.search(r"قیمت\s*یورو|یورو\s*چند", t, re.I):
        return "price_euro", cleaned
    if re.search(r"قیمت\s*طلا|طلای\s*۱۸|گرم\s*۱۸|طلا\s*چند", t, re.I):
        return "price_gold", cleaned
    if re.search(r"(بیتکوین|بیت‌کوین|اتریوم|تتر|btc|eth|usdt)", low) and re.search(
        r"قیمت|چند|چقدر|نرخ", t, re.I
    ):
        return "crypto", cleaned
    if re.search(r"هوا|آب\s*و\s*هوا|دما", t, re.I):
        return "weather", cleaned

    # خرید
    if re.search(r"(?:پیدا\s*کن|برام\s*بخر|میخوام\s*بخرم|لینک(?:ش)?\s*بفرست)", t, re.I):
        return "shop", cleaned
    if re.search(r"(?:باتری|باطری|شارژر|گوشی|ساعت)", t, re.I) and re.search(
        r"(?:پیدا|بخر|قیمت|چند|میخوام)", t, re.I
    ):
        return "shop", cleaned

    # vision فقط وقتی به عکس اشاره شده — نه هر «تحلیل»
    if re.search(r"(?:این\s*عکس|این\s*تصویر|عکس\s*رو|تصویر\s*رو|اینو\s*تحلیل|اینا\s*تحلیل|تحلیل\s*عکس|analyze\s*(?:this\s*)?(?:image|photo))", t, re.I):
        return "vision", cleaned
    if re.search(r"(?:اینو|اینا)\s*(?:ببین|چیه|چی میبینی)", t, re.I):
        return "vision", cleaned

    return "ai", cleaned
