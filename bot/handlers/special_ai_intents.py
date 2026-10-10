"""Live product-price gate — نسخه هوشمند v2.

قبل از AI عمومی، تشخیص می‌دهد آیا پیام واقعاً درخواست خرید/قیمت است.

هوشمندی‌ها:
- امتیازدهی چندسیگناله (نه فقط true/false ساده)
- فیلتر قوی سوالات غیرخرید (AI، آموزش، کد، سلامتی، هوا، …)
- تشخیص مدل/کد کالا (مثل HY510، A55، Note 13)
- حفظ بودجه و مشخصات در query
- حافظه کوتاه آخرین جستجوی خرید برای follow-up («لینکشون بفرست»)
"""

from __future__ import annotations

import re
import time
from typing import Optional


# ---------------------------------------------------------------------------
# حافظه کوتاه آخرین query خرید هر کاربر (برای follow-up لینک)
# ---------------------------------------------------------------------------
_LAST_SHOP: dict[int, tuple[float, str]] = {}
_LAST_SHOP_TTL = 600.0  # 10 دقیقه


def remember_shop_query(user_id: int, query: str) -> None:
    q = (query or "").strip()
    if user_id and q:
        _LAST_SHOP[int(user_id)] = (time.time(), q)
        # جلوگیری از رشد بی‌نهایت
        if len(_LAST_SHOP) > 5000:
            cutoff = time.time() - _LAST_SHOP_TTL
            dead = [k for k, (t, _) in _LAST_SHOP.items() if t < cutoff]
            for k in dead:
                _LAST_SHOP.pop(k, None)


def get_last_shop_query(user_id: int) -> Optional[str]:
    item = _LAST_SHOP.get(int(user_id or 0))
    if not item:
        return None
    ts, q = item
    if time.time() - ts > _LAST_SHOP_TTL:
        _LAST_SHOP.pop(int(user_id), None)
        return None
    return q


# ---------------------------------------------------------------------------
# نرمال‌سازی
# ---------------------------------------------------------------------------
def _normalize(text: str) -> str:
    s = str(text or "").strip()
    s = s.replace("ي", "ی").replace("ك", "ک")
    s = re.sub(r"[\u200c\u200f\u200e]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s


# ---------------------------------------------------------------------------
# فیلترهای منفی قوی — این‌ها هرگز خرید نیستند
# ---------------------------------------------------------------------------
_MARKET_RE = re.compile(
    r"(?:تحلیل|آنالیز|analysis|analyze|"
    r"کریپتو|رمزارز|crypto|بیت\s*کوین|bitcoin|\bbtc\b|"
    r"اتریوم|ethereum|\beth\b|تتر|usdt|سولانا|solana|\bsol\b|"
    r"فارکس|forex|حمایت|مقاومت|\bRSI\b|\bADX\b|\bATR\b|BOS|CHOCH|"
    r"لانگ|شورت|ترید|\btrade\b|trading|سیگنال|تایم\s*فریم|"
    r"funding|open\s*interest|"
    # ارز بدون کالای فیزیکی
    r"(?:قیمت\s+)?(?:دلار|یورو|پوند|درهم|لیر|یوان|روبل|افغانی|دینار|"
    r"usd|eur|gbp|aed|try|cny|rub|afn|iqd)\b|"
    r"(?:نرخ|چند(?:ه)?)\s+(?:دلار|یورو|طلا)|"
    r"\bgold\b|xau|انس\s*طلا)",
    re.I,
)

_AI_META_RE = re.compile(
    r"(?:"
    r"هوش\s*مصنوعی|artificial\s*intelligence|\bai\b|"
    r"چت\s*بات|chat\s*?bot|ربات|\bbot\b|"
    r"gemini|gpt|claude|grok|llama|openai|open\s*router|groq|cerebras|cloudflare|"
    r"کدوم\s*مدل|کدام\s*مدل|چه\s*مدل(?:ی)?\s*(?:هست|داری|هستی)|"
    r"مدل\s*(?:هوش|ai|فعال|فعلی|چت)|"
    r"کی\s*هستی|چی\s*هستی|چه\s*هستی|who\s*are\s*you|what\s*model|"
    r"کدام\s*سرویس|کدوم\s*سرویس|ارائه‌?دهنده|provider|"
    r"حافظه\s*(?:رو\s*)?(?:پاک|حذف)|حذف\s*حافظه|پاک\s*کردن\s*حافظه"
    r")",
    re.I,
)

# آموزش / چطور کار می‌کند / تعریف — نه خرید
_HOWTO_RE = re.compile(
    r"(?:"
    r"چطور|چگونه|how\s*to|"
    r"آموزش|یاد\s*بگیر|توضیح\s*بده|یعنی\s*چی|"
    r"معنی|تعریف|"
    r"فرق|تفاوت|"
    r"چرا\s*(?:این|اینجوری|این‌طور)|"
    r"کد\s*(?:بزن|بنویس|python|جاوا|برنامه)|"
    r"برنامه‌?\s*نویسی|الگوریتم|دیباگ|"
    r"بزنم|نصب\s*کنم|استفاده\s*کنم"  # «چطور … بزنم»
    r")",
    re.I,
)

# سلامتی / پزشکی / حقوقی / احساسات — نه خرید
_NON_SHOP_TOPIC_RE = re.compile(
    r"(?:"
    r"درد|بیمار|دکتر|دارو|نسخه|علائم|درمان|"
    r"افسرده|استرس|اضطراب|ازدواج|طلاق|وکیل|"
    r"هوا|آب\s*و\s*هوا|بارون|برف|دمای\s*هوا|"
    r"جوک|شعر|داستان\s*بگو|قصه|"
    r"ترجمه\s*کن|translate|"
    r"ساعت\s*چنده|تاریخ\s*امروز"
    r")",
    re.I,
)

# ---------------------------------------------------------------------------
# سیگنال‌های مثبت خرید
# ---------------------------------------------------------------------------
# کالاهای مشخص (قوی)
_PRODUCT_STRONG_RE = re.compile(
    r"(?:"
    # موبایل و برند
    r"آیفون|iphone|سامسونگ|samsung|گلکسی|galaxy|"
    r"شیائومی|xiaomi|ردمی|redmi|پوکو|poco|آنر|honor|هواوی|huawei|"
    r"ریلمی|realme|نوکیا|nokia|گوگل\s*پیکسل|pixel|"
    r"گوشی|موبایل|smartphone|تبلت|tablet|ipad|آیپد|"
    # لپ‌تاپ و کامپیوتر
    r"لپ\s*تاپ|لپتاپ|laptop|مک\s*بوک|macbook|آیمک|imac|"
    r"کامپیوتر|سیستم\s*اسمبل|مانیتور|monitor|"
    r"کیبورد|keyboard|ماوس|mouse|هید|"
    r"پردازنده|\bcpu\b|گرافیک|\bgpu\b|کارت\s*گرافیک|"
    r"مادربرد|motherboard|پاور\s*سیستم|\bpsu\b|"
    r"\bssd\b|\bhdd\b|هارد|"
    # «رم» فقط وقتی جدا یا با سیستم/لپ بیاید — نه داخل «بخرم»
    r"(?<![\u0600-\u06FFa-zA-Z])رم(?:\s*(?:سیستم|لپ|کامپیوتر))?|(?<![\w])ram(?![\w])|"
    r"خمیر\s*سیلیکون|خمیر\s*حرارتی|thermal\s*paste|کولر|cooler|فن\s*کیس|"
    # لوازم جانبی
    r"هدفون|هندزفری|headphone|earbuds|ایرپاد|airpods|"
    r"شارژر|charger|کابل|پاوربانک|powerbank|"
    r"ساعت\s*هوشمند|smartwatch|اپل\s*واچ|apple\s*watch|"
    r"دوربین|camera|لنز|"
    # گیم
    r"کنسول|پلی\s*استیشن|playstation|\bps5\b|\bps4\b|xbox|نینتندو|nintendo|"
    # خانه و پوشاک
    r"تلویزیون|\btv\b|یخچال|ماشین\s*لباسشویی|جاروبرقی|"
    r"کتانی|کفش|لباس|عطر|perfume|"
    r"پرینتر|printer"
    r")",
    re.I,
)

# کد/مدل کالا: HY510، Redmi Note 13، A55، 13T Pro
_PRODUCT_CODE_RE = re.compile(
    r"(?:"
    r"\b[A-Z]{1,4}\d{2,4}[A-Z]?\b|"  # HY510, A55, C71
    r"\b(?:note|redmi|poco|galaxy|iphone)\s*[\d]+(?:\s*(?:pro|plus|max|ultra|fe))?\b|"
    r"\b\d{1,2}[Tt]\s*(?:pro|plus)?\b|"  # 13T Pro
    r"مدل\s+[A-Za-z0-9][A-Za-z0-9\s\-]{1,20}"
    r")",
    re.I,
)

# افعال و قصد خرید
_ACTION_RE = re.compile(
    r"(?:"
    r"قیمت|نرخ|چنده|چقدر\s*(?:می(?:‌)?شه|است|ه)|"
    r"ارزان(?:\s*ترین)?|گران(?:\s*ترین)?|اقتصادی|به‌?صرفه|"
    r"خرید|بخرم|بخریم|بخر|بخری|بخره|"
    r"فروشگاه|فروشنده|سفارش|"
    r"لینک(?:ش|شون|ها)?|"
    r"موجود|موجودی|مقایسه|"
    r"بهترین|پیشنهاد|"
    r"چی\s*بخر|چه\s*بخر|کدوم\s*(?:رو\s*)?بخر|"
    r"دنبال|می\s*گردم|می‌گردم|میگردم|بگرد|بگردون|"
    r"پیدا\s*کن|پیدا\s*کنم|جستجو|سرچ|"
    r"می\s*خوام|میخوام|می‌خوام|نیاز\s*دارم|لازم\s*دارم|"
    r"از\s*کجا\s*بخر|"
    r"\bbuy\b|\bprice\b|\bshop\b|\bseller\b|\blink\b|"
    r"cheapest|looking\s*for|find\s*me"
    r")",
    re.I,
)

_BUDGET_RE = re.compile(
    r"(?:"
    r"(?:تا|زیر|حداکثر|حدود|حد|بودجه)\s*"
    r"[0-9۰-۹٠-٩]+(?:[.,٬]?[0-9۰-۹٠-٩]+)?\s*"
    r"(?:میلیون|میلیارد|م|هزار|تومان|تومن)?"
    r"|"
    r"[0-9۰-۹٠-٩]+(?:[.,٬]?[0-9۰-۹٠-٩]+)?\s*"
    r"(?:میلیون|میلیارد|م)\s*(?:تومان|تومن)?"
    r")",
    re.I,
)

# follow-up خالص لینک بدون نام محصول
_LINK_FOLLOWUP_RE = re.compile(
    r"(?:"
    r"لینک(?:ش|شون|ها)?|"
    r"آدرس(?:ش|شون)?|"
    r"بفرست|بده|بفرستید|"
    r"از\s*کجا\s*بخرم|"
    r"کجا\s*(?:موجود|بخرم)"
    r")",
    re.I,
)

_GREETING_ONLY_RE = re.compile(
    r"^(?:سلام|درود|هی|hello|hi|صبح\s*بخیر|عصر\s*بخیر|شب\s*بخیر)[\s!.؟]*$",
    re.I,
)


# ---------------------------------------------------------------------------
# امتیازدهی هوشمند
# ---------------------------------------------------------------------------
def _score_product_request(text: str) -> tuple[float, dict]:
    """امتیاز ۰–۱۰۰ + جزئیات سیگنال‌ها."""
    s = _normalize(text)
    info: dict = {"signals": [], "blocks": []}

    if not s or len(s) < 2:
        return 0.0, info

    # بلوک‌های قطعی
    if _GREETING_ONLY_RE.match(s):
        info["blocks"].append("greeting")
        return 0.0, info
    if _AI_META_RE.search(s):
        info["blocks"].append("ai_meta")
        return 0.0, info
    if _MARKET_RE.search(s) and not _PRODUCT_STRONG_RE.search(s):
        info["blocks"].append("market")
        return 0.0, info
    if _HOWTO_RE.search(s):
        # آموزش/تعریف مگر اینکه صریحاً قصد خرید/قیمت باشد
        if not re.search(r"بخر|خرید|قیمت|لینک|سفارش|ارزان|فروشگاه", s, re.I):
            info["blocks"].append("howto")
            return 0.0, info
    if _NON_SHOP_TOPIC_RE.search(s) and not _PRODUCT_STRONG_RE.search(s):
        info["blocks"].append("non_shop_topic")
        return 0.0, info

    score = 0.0

    has_strong = bool(_PRODUCT_STRONG_RE.search(s))
    has_code = bool(_PRODUCT_CODE_RE.search(s))
    has_action = bool(_ACTION_RE.search(s))
    has_budget = bool(_BUDGET_RE.search(s))

    if has_strong:
        score += 40
        info["signals"].append("product")
    if has_code:
        score += 35
        info["signals"].append("product_code")
        # کد کالا به‌تنهایی (مثل HY510) کافی است
        words = [w for w in s.split() if len(w) > 1]
        if len(words) <= 3:
            score += 15
            info["signals"].append("bare_code")
    if has_action:
        score += 30
        info["signals"].append("action")
    if has_budget:
        score += 20
        info["signals"].append("budget")

    # ترکیب‌های قوی
    if has_strong and has_action:
        score += 15
        info["signals"].append("product+action")
    if has_strong and has_budget:
        score += 15
        info["signals"].append("product+budget")
    if has_code and has_action:
        score += 10
        info["signals"].append("code+action")

    # پیام خیلی کوتاه فقط نام محصول → احتمالاً جستجو
    words = [w for w in s.split() if len(w) > 1]
    if has_strong and 1 <= len(words) <= 6 and not has_action:
        score += 20
        info["signals"].append("bare_product")

    # جریمه جملات طولانی توضیحی بدون فعل خرید
    if len(words) > 20 and not has_action and not has_budget:
        score -= 25
        info["signals"].append("long_no_action")

    return max(0.0, min(100.0, score)), info


def is_live_product_request(text: str, user_id: int | None = None) -> bool:
    """True فقط برای درخواست واقعی خرید/قیمت/بودجه."""
    s = _normalize(text)

    # follow-up لینک بعد از جستجوی قبلی
    if user_id and _LINK_FOLLOWUP_RE.search(s) and not _PRODUCT_STRONG_RE.search(s):
        if get_last_shop_query(user_id):
            # جمله کوتاه follow-up
            if len(s.split()) <= 8:
                return True

    score, _info = _score_product_request(s)
    return score >= 45.0


def _shopping_query(text: str, user_id: int | None = None) -> str:
    """استخراج query تمیز برای موتور خرید."""
    s = _normalize(text)

    # follow-up لینک → آخرین query
    if user_id and _LINK_FOLLOWUP_RE.search(s) and not _PRODUCT_STRONG_RE.search(s):
        last = get_last_shop_query(user_id)
        if last:
            return last

    patterns = [
        r"لطفاً|لطفا",
        r"میشه(?:\s*بگی)?",
        r"ببین|برام|برای\s*من",
        r"می\s*خوام|میخوام|می‌خوام|نیاز\s*دارم|لازم\s*دارم",
        r"دنبال",
        r"می\s*گردم|می‌گردم|میگردم|بگرد(?:ون)?",
        r"پیدا\s*کن(?:م)?|جستجو|سرچ",
        r"سلام|درود",
        r"قیمت|نرخ|چنده|چقدر",
        r"خرید|بخرم|بخریم|بخر|بخری",
        r"فروشگاه|فروشنده|سفارش",
        r"لینک(?:ش|شون|ها)?",
        r"ارزان(?:\s*ترین)?|گران(?:\s*ترین)?|اقتصادی|به‌?صرفه",
        r"بهترین|پیشنهاد|مقایسه|موجودی|موجود",
        r"چی\s*بخرم|چه\s*بخرم|کدوم\s*(?:رو\s*)?بخرم",
        r"(?<![\w\u0600-\u06FF])(?:یه|یک)(?![\w\u0600-\u06FF])",
        r"\bbuy\b|\bprice\b|\bshop\b|\bseller\b|\blink\b|cheapest|best|compare|available",
        r"looking\s*for|find\s*me",
        r"بفرست|بده",
    ]
    for p in patterns:
        s = re.sub(p, " ", s, flags=re.I)
    s = re.sub(r"[؟?!,:;]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


async def run_live_product_search(update, user_id: int, text: str) -> bool:
    """اجرای موتور خرید زنده و مصرف کامل درخواست."""
    query = _shopping_query(text, user_id=user_id)
    if len(query) < 2:
        await update.message.reply_text(
            "⚠️ نام یا مدل محصول برای استعلام قیمت مشخص نیست."
        )
        return True

    notice = await update.message.reply_text(
        "🔎 در حال استعلام زنده قیمت و فروشنده‌ها..."
    )
    try:
        from bot.features.market.shopping import search_shopping

        result = await search_shopping(
            query,
            source="all",
            max_results=8,
            user_id=user_id,
        )
        remember_shop_query(user_id, query)
        await update.message.reply_text(result)
    except Exception:
        from bot.logger import logger

        logger.exception(
            "live product search failed for user=%s query=%r", user_id, query
        )
        await update.message.reply_text(
            "⚠️ استعلام زنده قیمت فعلاً در دسترس نیست؛ قیمت حدسی ارائه نمی‌کنم."
        )
    finally:
        try:
            await notice.delete()
        except Exception:
            pass
    return True
