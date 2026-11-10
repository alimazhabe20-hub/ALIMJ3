"""تشخیص هوشمند نیت — بدون حذف قابلیت‌ها."""
from __future__ import annotations

import re
from typing import Optional, Tuple, Dict, Any


# پاک کردن حافظه: «پاک کردن حافظه»، «حذف حافظه ربات»، «حافظه رو پاک کن»، «ریست حافظه»، «همه چی رو فراموش کن»
CLEAR_MEMORY_RE = re.compile(
    r"(?:پاک\s*(?:کردن|کن)\s*(?:ی\s*)?حافظه|حذف\s*(?:کردن\s*)?حافظه|ریست\s*حافظه|"
    r"حافظه\s*(?:ات|ت|ی\s*ربات|ربات|گروه)?\s*(?:را|رو|و)?\s*(?:پاک|حذف|ریست)|"
    r"(?:همه\s*چی|همه\s*چیز|همه\s*رو)\s*(?:رو|را)?\s*فراموش\s*کن|clear\s*memory|reset\s*memory)",
    re.I,
)

# روشن/خاموش کردن هوش مصنوعی گروه با متن (فقط ادمین)
TOGGLE_AI_RE = re.compile(r"^\s*(?:ربات\s*)?(خاموش|روشن|غیرفعال|فعال)\s*(?:شو|کن|باش)?\s*[.!؟?]*\s*$", re.I)

# درخواست‌های مبهم که بدون موضوع معنا ندارند
VAGUE_RE = re.compile(r"^\s*(?:تحلیل\s*کن|تحلیلش\s*کن|توضیح\s*بده|بررسی\s*کن|نظرت\s*چیه)\s*[.!؟?]*\s*$", re.I)


def _clean(text: str) -> str:
    t = (text or "").strip()
    t = re.sub(r"^(?:ربات|هوشمند|!)\s*", "", t, flags=re.I).strip()
    t = re.sub(r"^/(?:ask|ai)(?:@\w+)?\s*", "", t, flags=re.I).strip()
    return t or (text or "").strip()


def detect_intent(text: str, *, has_reply_media: bool = False, is_reply_to_bot: bool = False) -> Tuple[str, str]:
    """
    Returns (intent, cleaned_query)

    intents:
      help, download, price_dollar, price_euro, price_gold, crypto,
      analyze_gold, analyze_crypto, weather, shop, vision, memory,
      summary, clear_memory, followup, ai
    """
    t = (text or "").strip()
    if not t:
        return "help", ""

    low = t.lower()
    cleaned = _clean(t)

    # حافظه / خلاصه
    if CLEAR_MEMORY_RE.search(t):
        return "clear_memory", cleaned
    if re.search(r"(?:حافظه\s*گروه|وضعیت\s*حافظه)", t, re.I):
        return "memory", cleaned
    if re.search(
        r"(?:خلاصه|جمع.?بندی).{0,18}(?:مکالمه|گفتگو|گروه)|(?:مکالمه|گفتگو).{0,18}(?:خلاصه|جمع.?بندی)|خلاصه\s*گروه",
        t,
        re.I,
    ):
        return "summary", cleaned

    if cleaned in {"ربات", "هوشمند", "!", "bot", "help", "راهنما"} or re.fullmatch(r"ربات\s*", t):
        return "help", cleaned

    # دانلود
    if re.search(r"https?://|www\.", t, re.I) and re.search(
        r"(instagram|tiktok|facebook|twitter|x\.com|youtube|youtu\.be|vimeo)", t, re.I
    ):
        return "download", cleaned

    # تحلیل بازار قبل از vision
    if re.search(r"تحلیل\s*طلا|طلا\s*را?\s*تحلیل|analyze\s*gold", t, re.I):
        return "analyze_gold", cleaned
    if re.search(
        r"تحلیل\s*(?:بیتکوین|بیت‌کوین|اتریوم|کریپتو|btc|eth)|(?:بیتکوین|btc)\s*را?\s*تحلیل",
        t,
        re.I,
    ):
        return "analyze_crypto", cleaned

    # قیمت‌ها
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

    # هوا — استخراج شهر در fast_path
    if re.search(r"هوا|آب\s*و\s*هوا|دما", t, re.I):
        return "weather", cleaned

    # خرید
    if re.search(r"(?:پیدا\s*کن|برام\s*بخر|میخوام\s*بخرم|لینک(?:ش)?\s*بفرست)", t, re.I):
        return "shop", cleaned
    if re.search(r"(?:باتری|باطری|شارژر|گوشی|ساعت|لپ\s*تاپ)", t, re.I) and re.search(
        r"(?:پیدا|بخر|قیمت|چند|میخوام|لینک)", t, re.I
    ):
        return "shop", cleaned

    # vision: مدیا در reply یا اشاره صریح به عکس
    if has_reply_media and re.search(
        r"(?:تحلیل|اینو|اینا|ببین|چیه|توضیح|describe|analyze)", t, re.I
    ):
        return "vision", cleaned
    if re.search(
        r"(?:این\s*عکس|این\s*تصویر|عکس\s*رو|تصویر\s*رو|اینو\s*تحلیل|اینا\s*تحلیل|تحلیل\s*عکس)",
        t,
        re.I,
    ):
        return "vision", cleaned

    # follow-up کوتاه وقتی به پیام ربات ریپلای شده
    if is_reply_to_bot and len(cleaned) <= 80:
        if re.search(
            r"(?:بیشتر|ادامه|چرا|چطور|یعنی چی|مثلا|توضیح|جزئیات|خب|بعدش|دیگه چی|همان|همون)",
            t,
            re.I,
        ):
            return "followup", cleaned
        # سؤال کوتاه هم followup است
        if cleaned.endswith("؟") or cleaned.endswith("?"):
            return "followup", cleaned

    return "ai", cleaned


def extract_entities(text: str) -> Dict[str, Any]:
    """استخراج سبک موجودیت‌ها برای مسیرهای ابزار."""
    t = text or ""
    out: Dict[str, Any] = {}
    m = re.search(r"(?:هوای|آب[‌ ]?و[‌ ]?هوای|دمای)\s+([^\s?؟،,]+)", t)
    if m:
        out["city"] = m.group(1).strip()
    m = re.search(r"(?:تا|زیر|حداکثر)\s*([\d۰-۹,،]+)\s*(?:هزار|میلیون)?\s*تومان", t)
    if m:
        out["budget_hint"] = m.group(0)
    if re.search(r"ایفون|iphone|آیفون", t, re.I):
        out["product_family"] = "iphone"
    if re.search(r"باتری|باطری", t, re.I):
        out["product"] = "battery"
    return out


def is_addressed_to_bot(text: str, bot_username: str = "") -> bool:
    t = text or ""
    if re.search(r"(?:^|\s)(?:ربات|هوشمند|دستیار)\b", t, re.I):
        return True
    if bot_username and f"@{bot_username.lower()}" in t.lower():
        return True
    if t.strip().startswith("!") or t.strip().startswith("/ask") or t.strip().startswith("/ai"):
        return True
    return False
