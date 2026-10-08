"""هوش خرید بازار — Shopping Engine v3.2 (نسخه توسعه‌یافته)

جستجوی زنده و چندفروشگاهی قیمت محصول در بازار ایران (پیش‌فرض)
+ اینستاگرام + در صورت درخواست کاربر، منابع خارجی.

قوانین:
- بازار ایران پیش‌فرض است؛ منابع خارجی فقط با درخواست صریح فعال می‌شوند.
- قیمت حدسی ارائه نمی‌شود؛ فقط قیمت استخراج‌شده از API یا صفحه محصول.
- هیچ وابستگی اجباری به AI ندارد.
- تاریخچه قیمت و هشدار قیمت پشتیبانی می‌شود.

توسعه‌های v3.2:
- Retry + Circuit Breaker + کش دو لایه
- اولویت دیجی‌کالا، فیلتر استوک، اعتبار قیمت
- Fallback HTML دیجی‌کالا
- حداقل دو منبع در خروجی
- اعتبارسنجی متقابل قیمت بین منابع
- حالت پیشنهاد vs ارزان‌ترین
- Value Score + اولویت رجیستری
- خلاصه بودجه و جدول مقایسه مدل‌ها
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import random
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable
from urllib.parse import quote_plus, urlparse

import httpx
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
try:
    from bot.logger import logger
except Exception:  # pragma: no cover
    import logging
    logger = logging.getLogger("rooze_ziba")

# ---------------------------------------------------------------------------
# Optional Redis (graceful fallback)
# ---------------------------------------------------------------------------
_REDIS = None
try:
    import redis.asyncio as aioredis  # type: ignore

    async def _init_redis() -> Any:
        global _REDIS
        try:
            client = aioredis.from_url(
                "redis://localhost:6379/0",
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=1.5,
            )
            await client.ping()
            _REDIS = client
            logger.info("shopping: Redis connected")
        except Exception:
            _REDIS = None
except Exception:
    aioredis = None  # type: ignore


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36 RoozeZiba/5.0"
)
CACHE_TTL = 180
INSPECT_CONCURRENCY = 6
MAX_RETRIES = 3
CIRCUIT_FAIL_THRESHOLD = 4
CIRCUIT_COOLDOWN = 90  # seconds

_CACHE: dict[str, tuple[float, list[dict]]] = {}
_STATS = {
    "searches": 0,
    "cache_hits": 0,
    "direct_ok": 0,
    "web_ok": 0,
    "empty": 0,
    "errors": 0,
    "retries": 0,
    "circuit_open": 0,
}
_SEARCH_SEM = asyncio.Semaphore(8)
_INSPECT_SEM = asyncio.Semaphore(INSPECT_CONCURRENCY)

# Circuit breaker state: source → (fail_count, open_until)
_CIRCUIT: dict[str, tuple[int, float]] = {}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class ProductResult:
    source: str
    title: str
    url: str
    price: int | None = None
    old_price: int | None = None
    currency: str = "تومان"
    seller: str = ""
    availability: str = ""
    image: str = ""
    match_hint: str = ""
    specs: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Source maps
# ---------------------------------------------------------------------------
IRAN_SITES = {
    "torob.com": "ترب",
    "digikala.com": "دیجی‌کالا",
    "technolife.ir": "تکنولایف",
    "snappshop.ir": "اسنپ‌شاپ",
    "emalls.ir": "ایمالز",
    "mobile.ir": "موبایل.ir",
    "basalam.com": "باسلام",
    "digistyle.com": "دیجی‌استایل",
    "modiseh.com": "مدیسه",
    "meghdadit.com": "مقداد آی‌تی",
    "kalaoma.com": "کالاوما",
    "19kala.com": "۱۹کالا",
}

FOREIGN_ALIASES = {
    "amazon": "amazon.com",
    "آمازون": "amazon.com",
    "ebay": "ebay.com",
    "ایبی": "ebay.com",
    "aliexpress": "aliexpress.com",
    "علی اکسپرس": "aliexpress.com",
    "علی‌اکسپرس": "aliexpress.com",
    "walmart": "walmart.com",
    "وال مارت": "walmart.com",
    "bestbuy": "bestbuy.com",
    "best buy": "bestbuy.com",
    "etsy": "etsy.com",
    "اتسی": "etsy.com",
    "newegg": "newegg.com",
    "noon": "noon.com",
    "نون": "noon.com",
    "temu": "temu.com",
    "تیمو": "temu.com",
    "shein": "shein.com",
    "شین": "shein.com",
}

IRAN_ALIASES = {
    "دیجی کالا": "digikala.com",
    "دیجی‌کالا": "digikala.com",
    "digikala": "digikala.com",
    "ترب": "torob.com",
    "torob": "torob.com",
    "تکنولایف": "technolife.ir",
    "technolife": "technolife.ir",
    "اسنپ شاپ": "snappshop.ir",
    "اسنپ‌شاپ": "snappshop.ir",
    "snappshop": "snappshop.ir",
    "ایمالز": "emalls.ir",
    "emalls": "emalls.ir",
    "موبایل دات آی آر": "mobile.ir",
    "mobile.ir": "mobile.ir",
    "باسلام": "basalam.com",
    "basalam": "basalam.com",
    "دیجی استایل": "digistyle.com",
    "دیجی‌استایل": "digistyle.com",
}

TRUST = {
    "دیجی‌کالا": 100,
    "ترب": 96,
    "تکنولایف": 94,
    "ایمالز": 92,
    "اسنپ‌شاپ": 91,
    "باسلام": 86,
    "دیجی‌استایل": 88,
    "مدیسه": 85,
    "موبایل.ir": 84,
    "مقداد آی‌تی": 83,
    "کالاوما": 82,
    "۱۹کالا": 81,
    "وب": 60,
}

SOURCES = {
    "torob": {"label": "ترب", "domains": ["torob.com"]},
    "digikala": {"label": "دیجی‌کالا", "domains": ["digikala.com"]},
    "snappshop": {"label": "اسنپ‌شاپ", "domains": ["snappshop.ir"]},
    "emalls": {"label": "ایمالز", "domains": ["emalls.ir"]},
    "basalam": {"label": "باسلام", "domains": ["basalam.com"]},
    "technolife": {"label": "تکنولایف", "domains": ["technolife.ir"]},
    "momtaz": {"label": "مقداد آی‌تی", "domains": ["meghdadit.com"]},
    "kalaoma": {"label": "کالاوما", "domains": ["kalaoma.com"]},
    "19kala": {"label": "۱۹کالا", "domains": ["19kala.com"]},
    "mobile": {"label": "موبایل‌دات‌آی‌آر", "domains": ["mobile.ir"]},
    "digistyle": {"label": "دیجی‌استایل", "domains": ["digistyle.com"]},
    "modiseh": {"label": "مدیسه", "domains": ["modiseh.com"]},
    "instagram": {"label": "اینستاگرام", "domains": ["instagram.com"]},
    "general": {"label": "وب / سایر", "domains": []},
}

_SOURCE_SEARCH_URLS = {
    "technolife.ir": "https://www.technolife.ir/search?search={q}",
    "snappshop.ir": "https://snappshop.ir/search/{q}",
    "emalls.ir": "https://emalls.ir/Search.aspx?search={q}",
    "meghdadit.com": "https://meghdadit.com/search?q={q}",
    "kalaoma.com": "https://kalaoma.com/search?q={q}",
    "19kala.com": "https://www.19kala.com/search/?q={q}",
    "mobile.ir": "https://www.mobile.ir/phones/search.aspx?search={q}",
}

INSTA_KEYWORDS = [
    "فروشگاه", "شاپ", "خرید", "قیمت", "فروش آنلاین", "online shop",
    "فروشگاه اینترنتی", "خرید آنلاین",
]

# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------
def _circuit_is_open(source: str) -> bool:
    state = _CIRCUIT.get(source)
    if not state:
        return False
    fails, open_until = state
    if time.time() < open_until:
        _STATS["circuit_open"] += 1
        return True
    # cooldown expired → half-open (reset)
    if fails >= CIRCUIT_FAIL_THRESHOLD:
        _CIRCUIT[source] = (0, 0.0)
    return False


def _circuit_record_success(source: str) -> None:
    _CIRCUIT[source] = (0, 0.0)


def _circuit_record_failure(source: str) -> None:
    fails, _ = _CIRCUIT.get(source, (0, 0.0))
    fails += 1
    open_until = time.time() + CIRCUIT_COOLDOWN if fails >= CIRCUIT_FAIL_THRESHOLD else 0.0
    _CIRCUIT[source] = (fails, open_until)
    if open_until:
        logger.warning("shopping circuit OPEN for %s (%d fails)", source, fails)


# ---------------------------------------------------------------------------
# Retry helper (no external dependency)
# ---------------------------------------------------------------------------
async def _with_retry(
    coro_factory: Callable[[], Awaitable[Any]],
    *,
    source: str = "generic",
    max_attempts: int = MAX_RETRIES,
    base_delay: float = 0.6,
) -> Any:
    """اجرای coroutine با retry نمایی + jitter و circuit breaker."""
    if _circuit_is_open(source):
        return None
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            result = await coro_factory()
            _circuit_record_success(source)
            return result
        except Exception as exc:
            last_exc = exc
            _STATS["retries"] += 1
            _STATS["errors"] += 1
            if attempt >= max_attempts:
                _circuit_record_failure(source)
                logger.debug("shopping %s failed after %d attempts: %s", source, attempt, exc)
                break
            delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.35)
            await asyncio.sleep(delay)
    return None


# ---------------------------------------------------------------------------
# Cache (memory + optional Redis)
# ---------------------------------------------------------------------------
async def _cache_get(key: str) -> list[dict] | None:
    # memory first
    cached = _CACHE.get(key)
    if cached and time.time() - cached[0] < CACHE_TTL:
        _STATS["cache_hits"] += 1
        return [dict(x) for x in cached[1]]
    # redis
    if _REDIS is not None:
        try:
            raw = await _REDIS.get(f"shop:{key}")
            if raw:
                data = json.loads(raw)
                _CACHE[key] = (time.time(), data)
                _STATS["cache_hits"] += 1
                return [dict(x) for x in data]
        except Exception:
            pass
    return None


async def _cache_set(key: str, rows: list[dict]) -> None:
    payload = [dict(x) for x in rows]
    _CACHE[key] = (time.time(), payload)
    if _REDIS is not None:
        try:
            await _REDIS.setex(f"shop:{key}", CACHE_TTL, json.dumps(payload, ensure_ascii=False))
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------
def _digits(text: str) -> str:
    return str(text or "").translate(
        str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    )


def _parse_price(value: Any) -> int | None:
    if value is None:
        return None
    s = _digits(str(value)).replace(",", "").replace("٬", "").strip()
    m = re.search(r"\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        n = float(m.group(0))
        return int(n) if n > 0 else None
    except Exception:
        return None



# کف/سقف معقول قیمت (تومان) برای فیلتر خطاهای واحد و آگهی‌های خراب
_PRICE_ABS_MIN = 50_000          # زیر این تقریباً همیشه خطاست
_PRICE_ABS_MAX = 2_000_000_000   # بالای این معمولاً ریال خام یا داده خراب است
_PHONE_FLOOR = 8_000_000         # کف معقول گوشی هوشمند نو در بازار ۱۴۰۵
_PHONE_KEYWORDS = (
    "گوشی", "موبایل", "smartphone", "iphone", "آیفون", "galaxy", "redmi",
    "poco", "پوکو", "شیائومی", "xiaomi", "سامسونگ", "samsung", "honor", "آنر",
)


def _looks_like_phone(title: str) -> bool:
    t = str(title or "").lower()
    return any(k in t for k in _PHONE_KEYWORDS)


def _normalize_market_price(raw: Any, title: str = "") -> int | None:
    """نرمال‌سازی قیمت به تومان + رد قیمت‌های غیرواقعی.

    - اگر عدد خیلی بزرگ باشد (احتمال ریال) ÷۱۰ می‌شود.
    - اگر برای گوشی خیلی پایین باشد، رد می‌شود.
    """
    p = _parse_price(raw)
    if p is None:
        return None

    # احتمال قیمت به ریال: اعداد خیلی بزرگ برای کالای معمول
    if p >= 500_000_000:
        p = p // 10
    elif p >= 200_000_000 and _looks_like_phone(title):
        p = p // 10

    if p < _PRICE_ABS_MIN or p > _PRICE_ABS_MAX:
        return None

    # گوشی هوشمند: قیمت‌های خیلی پایین در بازار ۱۴۰۵ معتبر نیستند
    # (مگر مدل‌های خیلی قدیمی/استوک که هنوز هم معمولاً بالای این کف‌اند)
    if _looks_like_phone(title) and p < _PHONE_FLOOR:
        # استثنا: اگر صریحاً لوازم جانبی باشد نه خود گوشی
        low = str(title or "").lower()
        accessory = any(
            x in low
            for x in (
                "قاب", "کاور", "گلس", "محافظ", "شارژر", "کابل", "هندزفری",
                "هدفون", "باتری", "جایگزین", "لوازم", "case", "cover", "glass",
            )
        )
        if not accessory:
            return None

    return int(p)


def _filter_price_outliers(rows: list[dict]) -> list[dict]:
    """حذف قیمت‌های پرت نسبت به میانهٔ نتایج هم‌دسته (مثلاً ÷۱۰ اشتباه)."""
    priced = [r for r in rows if r.get("price")]
    if len(priced) < 4:
        return rows
    prices = sorted(int(r["price"]) for r in priced)
    mid = prices[len(prices) // 2]
    if mid <= 0:
        return rows
    out: list[dict] = []
    for r in rows:
        p = r.get("price")
        if not p:
            out.append(r)
            continue
        # اگر از ۲۰٪ میانه کمتر یا ۵ برابر میانه بیشتر → مشکوک
        if p < mid * 0.20 or p > mid * 5:
            continue
        out.append(r)
    return out if out else rows


def _price_from_text(text: str) -> int | None:
    patterns = (
        r"([0-9۰-۹]{1,3}(?:[,٬][0-9۰-۹]{3}){1,4})\s*(?:تومان|تومن|ت)\b",
        r"([0-9۰-۹]{5,})\s*(?:تومان|تومن|ت)\b",
        r"(?:قیمت|price|قیمت فروش|قیمت نهایی)\s*[:：]?\s*([0-9۰-۹]{5,})",
    )
    for pat in patterns:
        m = re.search(pat, text or "", re.I)
        if m:
            p = _parse_price(m.group(1))
            if p:
                return p
    return None


def _currency_and_price(raw: Any, currency: str = "") -> tuple[int | None, str]:
    p = _parse_price(raw)
    cur = (currency or "").lower()
    if p is not None and ("rial" in cur or "ریال" in cur):
        p = p // 10
        return p, "تومان"
    if p is not None:
        return p, "تومان"
    return None, "تومان"


def _normalize_availability(raw: str) -> str:
    """نرمال‌سازی وضعیت موجودی به مقادیر استاندارد فارسی."""
    t = str(raw or "").strip().lower()
    if not t:
        return ""
    if any(
        x in t
        for x in (
            "instock", "in_stock", "in stock", "موجود", "available",
            "marketable", "httpschema.org/instock", "in_sale", "sale_on",
        )
    ):
        return "موجود"
    if any(
        x in t
        for x in (
            "outofstock", "out_of_stock", "out of stock", "ناموجود", "sold out",
            "httpschema.org/outofstock", "stop_production", "unavailable",
        )
    ):
        return "ناموجود"
    if any(x in t for x in ("preorder", "pre-order", "پیش‌فروش", "پیش فروش")):
        return "پیش‌فروش"
    if any(x in t for x in ("limited", "محدود")):
        return "موجودی محدود"
    # وضعیت‌های خام API را به فارسی نشکن؛ خالی برگردان
    if t in ("marketable", "none", "null", "unknown"):
        return "موجود" if t == "marketable" else ""
    if "/" in t:
        return t.split("/")[-1]
    # از نمایش مقادیر انگلیسی خام خودداری کن
    if re.fullmatch(r"[a-z0-9_\-]+", t):
        return ""
    return raw.strip()[:40]


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def _source_for_url(url: str) -> str:
    d = _domain(url)
    for key, cfg in SOURCES.items():
        if any(x in d for x in cfg["domains"]):
            return key
    return "general"


def _clean_title(title: str) -> str:
    title = re.sub(r"\s+", " ", title or "").strip()
    return title[:240]


def _clean_query(text: str) -> str:
    q = str(text or "").strip().replace("ي", "ی").replace("ك", "ک")
    q = re.sub(r"[\u200c\u200f\u200e]", " ", q)
    q = re.sub(
        r"(?:لطفاً|لطفا|میشه|میخوام|می\s*خوام|برام|برای\s*من|ببین|پیدا\s*کن|پیدا کن|"
        r"جستجو کن|جستجو|بگرد|خرید|بخر|بخرم|قیمت|نرخ|چنده|چقدر|فروشگاه|فروشنده|"
        r"لینک|مقایسه|ارزان(?:ترین)?|بهترین|پیشنهاد|موجودی|موجود|چی\s*بخرم|چه\s*بخرم)",
        " ",
        q,
        flags=re.I,
    )
    q = re.sub(r"(?:سایت|فروشگاه)\s+(?:خارجی|های خارجی|های ایرانی|ایرانی)", " ", q, flags=re.I)
    q = re.sub(r"https?://\S+", " ", q)
    q = re.sub(r"\s+", " ", q).strip(" ؟?!،,")
    return q or str(text or "").strip()


def _budget(text: str) -> int:
    t = _digits(text).replace(",", "").replace("٬", "")
    patterns = (
        r"(?:بودجه|تا|زیر|حداکثر|حدود|حد)\s*(\d+(?:\.\d+)?)\s*(?:میلیون|م)\b",
        r"(\d+(?:\.\d+)?)\s*(?:میلیون|م)\s*(?:تومان|تومن)?",
        r"(?:بودجه|تا|زیر|حداکثر|حدود|حد)\s*(\d{5,})\s*(?:تومان|تومن)?",
    )
    for pat in patterns:
        m = re.search(pat, t, re.I)
        if m:
            try:
                n = float(m.group(1))
                if "میلیون" in m.group(0) or re.search(r"\d+(?:\.\d+)?\s*م\b", m.group(0)):
                    n *= 1_000_000
                if n >= 100_000:
                    return int(n)
            except Exception:
                pass
    return 0


def _foreign_requested(text: str) -> bool:
    q = str(text or "").lower()
    markers = (
        "سایت خارجی", "سایت‌های خارجی", "سایت های خارجی", "بازار جهانی",
        "منابع خارجی", "بین‌المللی", "بین المللی", "خارجی",
        "amazon", "آمازون", "ebay", "ایبی", "aliexpress", "علی اکسپرس",
        "walmart", "best buy", "etsy", "newegg", "noon", "temu", "shein",
    )
    return any(x in q for x in markers)


def _explicit_domain(text: str) -> str:
    q = str(text or "").lower()
    for alias, domain in sorted({**IRAN_ALIASES, **FOREIGN_ALIASES}.items(), key=lambda x: -len(x[0])):
        if alias in q:
            return domain
    m = re.search(r"(?:https?://)?(?:www\.)?([a-z0-9][a-z0-9.-]+\.[a-z]{2,})(?:/[^\s]*)?", q)
    return m.group(1).lower().rstrip(".") if m else ""


def _tokens(text: str) -> set[str]:
    stop = {
        "برای", "من", "یک", "یه", "تا", "تومان", "قیمت", "خرید",
        "مردانه", "زنانه", "مناسب", "بهترین", "ارزان",
    }
    return {x for x in re.findall(r"[\wآ-ی]{2,}", str(text or "").lower()) if x not in stop}


def _relevance(title: str, query: str) -> float:
    qt = _tokens(query)
    tt = _tokens(title)
    if not qt:
        return 0.0
    aliases = {
        "شیائومی": "xiaomi", "xiaomi": "xiaomi",
        "ردمی": "redmi", "redmi": "redmi",
        "پوکو": "poco", "poco": "poco",
        "سامسونگ": "samsung", "samsung": "samsung",
        "اپل": "apple", "apple": "apple",
        "آیفون": "iphone", "iphone": "iphone",
        "آنر": "honor", "honor": "honor",
    }
    nq = {aliases.get(x, x) for x in qt}
    nt = {aliases.get(x, x) for x in tt}
    overlap = len(nq & nt) / max(1, len(nq))
    phrase = 25.0 if _clean_query(query).lower() in title.lower() else 0.0
    return overlap * 100 + phrase


def _cache_key(query: str, source: str, max_price: int, foreign: bool) -> str:
    raw = f"{query}|{source}|{max_price}|{foreign}".lower()
    return hashlib.sha1(raw.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Intent / product matching
# ---------------------------------------------------------------------------
_PHONE_POSITIVE = {
    "گوشی", "موبایل", "smartphone", "iphone", "آیفون", "اندروید", "android",
    "galaxy", "redmi", "poco", "پوکو", "pixel", "honor", "oneplus", "nokia",
    "شیائومی", "xiaomi", "سامسونگ", "samsung", "هواوی", "huawei", "realme", "ریلمی",
}
_PHONE_FEATURE_NEGATIVE = {
    "105", "106", "110", "150", "225", "3310", "simple", "feature phone",
    "دکمه‌ای", "دکمه ای", "دکمه‌اي", "ساده", "کیبوردی", "کیبورد دار", "کیبورددار",
}
_XIAOMI_WORDS = {"شیائومی", "xiaomi", "mi", "redmi", "poco", "پوکو", "ردمی"}
_SAMSUNG_WORDS = {"سامسونگ", "samsung", "galaxy"}
_BRAND_WORDS = {
    "شیائومی": _XIAOMI_WORDS, "xiaomi": _XIAOMI_WORDS,
    "سامسونگ": _SAMSUNG_WORDS, "samsung": _SAMSUNG_WORDS,
    "اپل": {"اپل", "apple", "iphone", "آیفون"}, "apple": {"اپل", "apple", "iphone", "آیفون"},
    "آنر": {"آنر", "honor"}, "honor": {"آنر", "honor"},
    "پوکو": {"پوکو", "poco"}, "poco": {"پوکو", "poco"},
}


def _shopping_intent(raw: str) -> dict:
    q = str(raw or "").strip().replace("ي", "ی").replace("ك", "ک").lower()
    q = re.sub(
        r"^\s*نه[،,:؛\s]+(?=(گوشی|موبایل|شیائومی|سامسونگ|پوکو|آیفون|iphone|xiaomi))",
        "",
        q,
        flags=re.I,
    )
    phone = bool(
        re.search(
            r"گوشی|موبایل|اسمارت\s*فون|smart\s*phone|smartphone|iphone|آیفون|"
            r"شیائومی|xiaomi|سامسونگ|samsung|پوکو|poco|redmi|ردمی|honor|oneplus|pixel",
            q,
            re.I,
        )
    )
    touch = bool(
        re.search(
            r"گوشی\s*(?:لمسی|هوشمند)|موبایل\s*(?:لمسی|هوشمند)|لمسی|smartphone|"
            r"اسمارت\s*فون|هوشمند",
            q,
            re.I,
        )
    )
    non_touch = bool(
        re.search(r"غیر\s*لمسی|غیرلمسی|دکمه(?:ای|‌ای)|ساده|کیبوردی|feature\s*phone", q, re.I)
    )
    brand = ""
    for b in (
        "شیائومی", "xiaomi", "سامسونگ", "samsung", "اپل", "apple",
        "آیفون", "honor", "آنر", "پوکو", "poco",
    ):
        if b in q:
            brand = b
            break
    # حالت: پیشنهاد هوشمند vs ارزان‌ترین
    cheapest_mode = bool(
        re.search(r"ارزان(?:\s*ترین)?|کمترین\s*قیمت|cheap(?:est)?", q, re.I)
    )
    suggest_mode = bool(
        re.search(
            r"بهترین|پیشنهاد|چی\s*بخر|چه\s*بخر|مناسب|ارزش\s*خرید|value|"
            r"راهنما|کدام|کدوم",
            q,
            re.I,
        )
    )
    if not cheapest_mode and not suggest_mode:
        # «تا X میلیون» بدون «ارزان» → پیشنهاد
        if re.search(r"(?:تا|زیر|بودجه|حداکثر)\s*[0-9۰-۹]", q):
            suggest_mode = True
    registry_pref = bool(
        re.search(r"رجیستر|رجیستری|ثبت\s*شده|ثبت‌شده", q, re.I)
    )
    return {
        "phone": phone,
        "touch": touch and not non_touch,
        "non_touch": non_touch,
        "brand": brand,
        "cheapest_mode": cheapest_mode,
        "suggest_mode": suggest_mode and not cheapest_mode,
        "registry_pref": registry_pref,
    }


def _shopping_brand_match(text: str, brand: str) -> bool:
    if not brand:
        return True
    low = str(text or "").lower()
    words = _BRAND_WORDS.get(brand, {brand})
    return any(w.lower() in low for w in words)


def _wants_used(query: str) -> bool:
    """کاربر صریحاً استوک/کارکرده خواسته؟"""
    q = str(query or "").lower()
    return bool(
        re.search(
            r"استوک|کارکرده|دست\s*دوم|دست‌دوم|used|refurbished|بازسازی|"
            r"در حد نو|درحد نو|آکبند\s*نمو?ده",
            q,
            re.I,
        )
    )


def _is_used_listing(text: str) -> bool:
    t = str(text or "").lower()
    return bool(
        re.search(
            r"استوک|کارکرده|دست\s*دوم|دست‌دوم|used|refurbished|"
            r"بازسازی|در حد نو|درحد نو|آکبند\s*نمو?ده|بدون\s*جعبه|"
            r"جعبه\s*باز|open\s*box|stock",
            t,
            re.I,
        )
    )


def _shopping_product_match(row: dict, query: str, intent: dict) -> bool:
    title = str(row.get("title") or "")
    snippet = str(row.get("snippet") or "")
    text = f"{title} {snippet}".lower()
    # پیش‌فرض: استوک/کارکرده حذف شود مگر کاربر صریحاً بخواهد
    if _is_used_listing(text) and not _wants_used(query):
        return False
    if intent.get("phone"):
        positive = any(x in text for x in _PHONE_POSITIVE)
        if not positive:
            return False
        if intent.get("touch") and any(x in text for x in _PHONE_FEATURE_NEGATIVE):
            if not any(
                x in text
                for x in ("smartphone", "اسمارت", "هوشمند", "android", "اندروید", "iphone", "آیفون")
            ):
                return False
    if intent.get("brand") and not _shopping_brand_match(text, intent["brand"]):
        return False
    return True


def _shopping_model_key(title: str) -> str:
    """کلید پایدار مدل — ظرفیت، رم، رنگ و تعداد سیم‌کارت حذف می‌شوند."""
    t = str(title or "").lower().replace("ي", "ی").replace("ك", "ک")
    # حذف کلمات عمومی
    t = re.sub(
        r"\b(گوشی|موبایل|mobile|phone|smartphone|اسمارت\s*فون|"
        r"شیائومی|xiaomi|سامسونگ|samsung|اپل|apple)\b",
        " ",
        t,
    )
    # ظرفیت / رم / حافظه
    t = re.sub(r"\b\d+\s*/\s*\d+\s*(?:gb|گیگ|گیگابایت)?\b", " ", t, flags=re.I)
    t = re.sub(r"\b\d+\s*(?:gb|گیگ|گیگابایت|گیک|مگابایت|mb|گ|tb|ترابایت)\b", " ", t, flags=re.I)
    t = re.sub(r"\b(?:رم|ram|حافظه|storage|internal)\s*\d+\b", " ", t, flags=re.I)
    t = re.sub(r"\b\d+\s*(?:رم|ram)\b", " ", t, flags=re.I)
    # سیم‌کارت و شبکه
    t = re.sub(r"\b(?:دو|2|تک|یک)\s*سیم(?:\s*کارت)?\b", " ", t, flags=re.I)
    t = re.sub(r"\b(?:4g|5g|lte|volte)\b", " ", t, flags=re.I)
    # رنگ‌های رایج
    t = re.sub(
        r"\b(?:مشکی|سیاه|سفید|آبی|سبز|قرمز|صورتی|بنفش|خاکستری|طلایی|نقره‌ای|"
        r"black|white|blue|green|red|pink|purple|gray|grey|gold|silver)\b",
        " ",
        t,
        flags=re.I,
    )
    # رجیستری / گارانتی / نسخه
    t = re.sub(
        r"\b(?:رجیستر|رجیستری|گارانتی|ضمانت|نسخه|ویرایش|edition|global|china)\b",
        " ",
        t,
        flags=re.I,
    )
    t = re.sub(r"[^\wآ-ی]+", " ", t)
    stop = {
        "مدل", "ظرفیت", "حافظه", "داخلی", "تومان", "با", "و", "برای",
        "رنگ", "رم", "ram", "خرید", "فروش", "جدید", "اصل",
    }
    toks = [x for x in t.split() if x not in stop and len(x) >= 2]
    return " ".join(toks[:10])


# ---------------------------------------------------------------------------
# JSON-LD & page inspection
# ---------------------------------------------------------------------------
def _extract_jsonld(soup: BeautifulSoup) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for tag in soup.select('script[type="application/ld+json"]'):
        try:
            obj = json.loads(tag.string or tag.get_text())
        except Exception:
            continue
        objs = obj if isinstance(obj, list) else [obj]
        for x in objs:
            if isinstance(x, dict):
                if x.get("@type") == "@graph" and isinstance(x.get("@graph"), list):
                    found.extend(y for y in x["@graph"] if isinstance(y, dict))
                else:
                    found.append(x)
    return found


def _from_product(obj: dict[str, Any]) -> tuple[int | None, int | None, str, str, str, str]:
    offers = obj.get("offers") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    if not isinstance(offers, dict):
        offers = {}
    price, cur = _currency_and_price(
        offers.get("price") or offers.get("lowPrice"),
        offers.get("priceCurrency", ""),
    )
    old = _parse_price(offers.get("highPrice") or offers.get("price"))
    seller = offers.get("seller")
    if isinstance(seller, dict):
        seller = seller.get("name") or ""
    availability = _normalize_availability(str(offers.get("availability") or ""))
    image = obj.get("image") or ""
    if isinstance(image, list):
        image = image[0] if image else ""
    return price, old, str(seller or ""), availability, str(image or ""), cur


def _jsonld_products(soup: BeautifulSoup, domain: str, limit: int) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for node in soup.select('script[type="application/ld+json"]'):
        raw = node.string or node.get_text(" ", strip=True)
        try:
            data = json.loads(raw)
        except Exception:
            continue
        stack = data if isinstance(data, list) else [data]
        expanded: list[Any] = []
        for obj in stack:
            if isinstance(obj, dict) and isinstance(obj.get("@graph"), list):
                expanded.extend(obj["@graph"])
            else:
                expanded.append(obj)
        for obj in expanded:
            if not isinstance(obj, dict):
                continue
            typ = str(obj.get("@type", "")).lower()
            if typ not in ("product", "productgroup"):
                continue
            title = str(obj.get("name") or "").strip()
            url = str(obj.get("url") or "").strip()
            if url.startswith("/"):
                url = f"https://{domain}{url}"
            offers = obj.get("offers") or {}
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            price = _parse_price(offers.get("price") if isinstance(offers, dict) else None)
            if not price and isinstance(offers, dict):
                price = _parse_price(offers.get("lowPrice"))
            avail = _normalize_availability(
                str(offers.get("availability", "")) if isinstance(offers, dict) else ""
            )
            if not title or not url or url in seen:
                continue
            seen.add(url)
            out.append(
                {
                    "title": title,
                    "url": url,
                    "price": price,
                    "seller": IRAN_SITES.get(domain, ""),
                    "source": IRAN_SITES.get(domain, domain),
                    "availability": avail,
                }
            )
            if len(out) >= limit:
                return out
    return out


async def _inspect(url: str, title: str, snippet: str) -> ProductResult:
    result = ProductResult(
        source=_source_for_url(url),
        title=title,
        url=url,
        match_hint=(snippet or "")[:220],
    )
    if result.source == "instagram":
        result.seller = "صفحه اینستاگرامی"
        return result

    async def _do_fetch() -> ProductResult:
        async with _INSPECT_SEM:
            async with httpx.AsyncClient(
                timeout=12.0, follow_redirects=True, headers={"User-Agent": UA}
            ) as client:
                r = await client.get(url)
                if r.status_code >= 400:
                    return result
                soup = BeautifulSoup(r.text, "html.parser")

                for obj in _extract_jsonld(soup):
                    typ = obj.get("@type")
                    if typ == "Product" or (isinstance(typ, list) and "Product" in typ):
                        p, old, seller, avail, image, cur = _from_product(obj)
                        if p is not None:
                            result.price = p
                        if old is not None and (result.price is None or old > result.price):
                            result.old_price = old
                        result.seller = seller or result.seller
                        result.availability = avail or result.availability
                        result.image = image
                        result.currency = cur
                        if result.price is not None:
                            break

                if result.price is None:
                    meta = soup.select_one(
                        'meta[property="product:price:amount"], '
                        'meta[itemprop="price"], '
                        'meta[property="og:price:amount"]'
                    )
                    if meta:
                        result.price, result.currency = _currency_and_price(
                            meta.get("content") or meta.get("value"),
                            meta.get("contentCurrency", "") or "تومان",
                        )

                if result.price is None:
                    text = soup.get_text(" ", strip=True)
                    patterns = [
                        r"([0-9۰-۹][0-9۰-۹,٬\.]{2,})\s*(?:تومان|تومن|ت\.?م)",
                        r"(?:قیمت|Price|قیمت نهایی|قیمت فروش)\s*[:：]?\s*([0-9۰-۹][0-9۰-۹,٬\.]{2,})",
                        r"([0-9۰-۹]{1,3}(?:[٬,][0-9۰-۹]{3})+)\s*(?:تومان|تومن)",
                    ]
                    for pat in patterns:
                        m = re.search(pat, text, re.I)
                        if m:
                            result.price, result.currency = _currency_and_price(
                                m.group(1), "تومان"
                            )
                            break

                # availability from text if still empty
                if not result.availability:
                    text_low = soup.get_text(" ", strip=True).lower()
                    if re.search(r"ناموجود|اتمام موجودی|out\s*of\s*stock", text_low):
                        result.availability = "ناموجود"
                    elif re.search(r"موجود\s*در\s*انبار|in\s*stock|آماده\s*ارسال", text_low):
                        result.availability = "موجود"

                og_title = soup.select_one('meta[property="og:title"]')
                if og_title and og_title.get("content"):
                    clean = _clean_title(og_title["content"])
                    if len(clean) > 8:
                        result.title = clean
                return result

    try:
        res = await _with_retry(lambda: _do_fetch(), source=f"inspect:{_domain(url)}", max_attempts=2)
        return res if isinstance(res, ProductResult) else result
    except Exception as exc:
        logger.debug("shopping inspect failed %s: %s", url, exc)
        return result


# ---------------------------------------------------------------------------
# Search engines
# ---------------------------------------------------------------------------
async def _bing_search(query: str, domain: str = "", limit: int = 8) -> list[dict]:
    if _circuit_is_open("bing"):
        return []

    async def _do() -> list[dict]:
        q = f"site:{domain} {query}" if domain else query
        url = f"https://www.bing.com/search?q={quote_plus(q)}&setlang=fa-IR"
        async with _SEARCH_SEM:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(12.0, connect=5.0),
                follow_redirects=True,
                headers={"User-Agent": UA, "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.7"},
            ) as client:
                r = await client.get(url)
        if r.status_code >= 400:
            raise RuntimeError(f"bing status {r.status_code}")
        soup = BeautifulSoup(r.text, "html.parser")
        out: list[dict] = []
        for item in soup.select("li.b_algo")[:limit]:
            a = item.select_one("h2 a")
            if not a:
                continue
            href = (a.get("href") or "").strip()
            title = a.get_text(" ", strip=True)
            cap = item.select_one(".b_caption p")
            snippet = cap.get_text(" ", strip=True) if cap else ""
            if href.startswith("http") and title:
                out.append({"url": href, "title": title, "snippet": snippet})
        if out:
            _STATS["web_ok"] += 1
        return out

    result = await _with_retry(_do, source="bing")
    return result if isinstance(result, list) else []


async def _ddg_search(query: str, domain: str = "", limit: int = 8) -> list[dict]:
    if _circuit_is_open("ddg"):
        return []

    async def _do() -> list[dict]:
        q = f"site:{domain} {query}" if domain else query
        async with _SEARCH_SEM:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(12.0, connect=5.0),
                follow_redirects=True,
                headers={"User-Agent": UA, "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.7"},
            ) as client:
                r = await client.get("https://html.duckduckgo.com/html/", params={"q": q})
        if r.status_code >= 400:
            raise RuntimeError(f"ddg status {r.status_code}")
        soup = BeautifulSoup(r.text, "html.parser")
        out: list[dict] = []
        for item in soup.select(".result")[:limit]:
            a = item.select_one(".result__a")
            if not a:
                continue
            href = (a.get("href") or "").strip()
            title = a.get_text(" ", strip=True)
            s = item.select_one(".result__snippet")
            snippet = s.get_text(" ", strip=True) if s else ""
            if href.startswith("http") and title:
                out.append({"url": href, "title": title, "snippet": snippet})
        return out

    result = await _with_retry(_do, source="ddg")
    return result if isinstance(result, list) else []


async def _fetch_source(query: str, domain: str, limit: int, foreign: bool) -> list[dict]:
    batches = await asyncio.gather(
        _bing_search(query, domain=domain, limit=limit),
        _ddg_search(query, domain=domain, limit=limit),
        return_exceptions=True,
    )
    out: list[dict] = []
    for b in batches:
        if isinstance(b, list):
            for x in b:
                host = urlparse(x.get("url", "")).netloc.lower().replace("www.", "")
                x["source"] = IRAN_SITES.get(host, host if foreign else "وب")
                x["price"] = _price_from_text(
                    (x.get("title") or "") + " " + (x.get("snippet") or "")
                )
                out.append(x)
    return out


# ---------------------------------------------------------------------------
# Direct catalog / API sources
# ---------------------------------------------------------------------------
async def _direct_torob(query: str, max_price: int, limit: int) -> list[dict]:
    if _circuit_is_open("torob"):
        return []

    async def _do() -> list[dict]:
        async with _SEARCH_SEM:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(11.0, connect=5.0),
                follow_redirects=True,
                headers={
                    "User-Agent": UA,
                    "Accept": "application/json",
                    "Accept-Language": "fa-IR,fa;q=0.9",
                },
            ) as client:
                r = await client.get(
                    "https://api.torob.com/v4/base-product/search/",
                    params={
                        "q": query,
                        "page": 0,
                        "size": min(max(12, limit * 2), 40),
                        # برای بودجه بالا sort=price فقط مدل‌های خیلی ارزان می‌آورد
                        **({"sort": "price"} if (max_price and max_price < 8_000_000) else {}),
                        "source": "torob_search",
                    },
                )
        if r.status_code >= 400:
            raise RuntimeError(f"torob status {r.status_code}")
        data = r.json()
        raw = data.get("results") if isinstance(data, dict) else None
        if not isinstance(raw, list):
            return []
        out: list[dict] = []
        seen: set[str] = set()
        for item in raw:
            if not isinstance(item, dict) or item.get("is_adv") is True:
                continue
            title = str(
                item.get("name1") or item.get("name") or item.get("title") or ""
            ).strip()
            # قیمت ترب معمولاً تومان است؛ با اعتبارسنجی واحد و کف بازار
            price = _normalize_market_price(
                item.get("price") if item.get("price") not in (None, 0, "0") else item.get("min_price"),
                title,
            )
            key = str(item.get("random_key") or item.get("prk") or "").strip()
            link = str(item.get("page_url") or item.get("url") or "").strip() or (
                f"https://torob.com/p/{key}/" if key else ""
            )
            avail = _normalize_availability(str(item.get("availability") or ""))
            if (
                not title
                or not price
                or not link
                or link in seen
                or (max_price and price > max_price)
            ):
                continue
            if _is_used_listing(title) and not _wants_used(query):
                continue
            seen.add(link)
            out.append(
                {
                    "title": title,
                    "url": link,
                    "price": price,
                    "seller": str(item.get("seller_name") or "").strip(),
                    "source": "ترب",
                    "availability": avail,
                }
            )
            if len(out) >= limit:
                break
        if out:
            _STATS["direct_ok"] += 1
        return out

    result = await _with_retry(_do, source="torob")
    return result if isinstance(result, list) else []



async def _digikala_html_fallback(query: str, max_price: int, limit: int) -> list[dict]:
    """Fallback وقتی API دیجی‌کالا خالی/خطا است: صفحه جستجو + JSON-LD."""
    if _circuit_is_open("digikala_html"):
        return []
    url = f"https://www.digikala.com/search/?q={quote_plus(query)}"

    async def _do() -> list[dict]:
        async with _SEARCH_SEM:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(12.0, connect=5.0),
                follow_redirects=True,
                headers={"User-Agent": UA, "Accept-Language": "fa-IR,fa;q=0.9"},
            ) as client:
                r = await client.get(url)
        if r.status_code >= 400:
            raise RuntimeError(f"digikala html {r.status_code}")
        soup = BeautifulSoup(r.text, "html.parser")
        out = _jsonld_products(soup, "digikala.com", limit)
        # نرمال قیمت و فیلتر
        cleaned: list[dict] = []
        for x in out:
            title = str(x.get("title") or "")
            p = _normalize_market_price(x.get("price"), title)
            if not p:
                continue
            if max_price and p > max_price:
                continue
            if _is_used_listing(title) and not _wants_used(query):
                continue
            x["price"] = p
            x["source"] = "دیجی‌کالا"
            x["seller"] = x.get("seller") or "دیجی‌کالا"
            x["_verified_direct"] = True
            cleaned.append(x)
            if len(cleaned) >= limit:
                break
        if cleaned:
            _STATS["direct_ok"] += 1
        return cleaned

    result = await _with_retry(_do, source="digikala_html", max_attempts=2)
    return result if isinstance(result, list) else []


def _cross_validate_prices(rows: list[dict]) -> list[dict]:
    """اگر یک مدل در چند منبع باشد، قیمت پرت را جریمه/حذف می‌کند."""
    by_model: dict[str, list[dict]] = {}
    for r in rows:
        mk = r.get("_model_key") or _shopping_model_key(str(r.get("title") or ""))
        if not mk or not r.get("price"):
            continue
        by_model.setdefault(mk, []).append(r)
    flagged: set[int] = set()
    for mk, items in by_model.items():
        if len(items) < 2:
            continue
        prices = sorted(int(x["price"]) for x in items)
        med = prices[len(prices) // 2]
        if med <= 0:
            continue
        for x in items:
            p = int(x["price"])
            # اختلاف بیش از ۳۵٪ از میانه → مشکوک
            if p < med * 0.65 or p > med * 1.35:
                x["_price_outlier"] = True
                x["_score"] = float(x.get("_score", 0)) - 20
            else:
                x["_cross_validated"] = True
                x["_score"] = float(x.get("_score", 0)) + 6
    # حذف outlierهای خیلی بد اگر جایگزین معتبر هست
    out: list[dict] = []
    for r in rows:
        if r.get("_price_outlier") and r.get("_model_key"):
            peers = by_model.get(r["_model_key"] or "", [])
            good = [p for p in peers if not p.get("_price_outlier")]
            if good:
                continue
        out.append(r)
    return out


def _value_score(row: dict, max_price: int, intent: dict) -> float:
    """امتیاز ارزش خرید: بودجه + رجیستری + تأیید + تازگی تقریبی."""
    s = 0.0
    title = str(row.get("title") or "").lower()
    price = row.get("price")
    if price and max_price and max_price > 0:
        ratio = float(price) / float(max_price)
        if intent.get("cheapest_mode"):
            s += max(0, 25 * (1.0 - ratio))
        elif intent.get("suggest_mode"):
            if 0.35 <= ratio <= 0.92:
                s += 28
            elif 0.20 <= ratio < 0.35:
                s += 12
            elif ratio < 0.15:
                s -= 10
        else:
            if 0.25 <= ratio <= 0.95:
                s += 18
    # رجیستری
    if re.search(r"رجیستر(?:ی| شده)?|ثبت[\s‌]?شده", title):
        s += 10
        if intent.get("registry_pref"):
            s += 8
    if re.search(r"غیر\s*رجیستر|بدون\s*رجیستر|not\s*regist", title):
        s -= 12
    if row.get("_verified_direct"):
        s += 6
    if row.get("_cross_validated"):
        s += 5
    if str(row.get("source") or "") == "دیجی‌کالا":
        s += 4
    # تازگی تقریبی از عدد مدل
    if re.search(r"\b(15|14|13|a7|a5|c81|c85|note\s*1[345])\b", title, re.I):
        s += 3
    return s


def _budget_profile_line(max_price: int, intent: dict, rows: list[dict]) -> str:
    if not max_price:
        return ""
    if max_price < 8_000_000:
        tier = "خیلی اقتصادی"
    elif max_price < 20_000_000:
        tier = "اقتصادی"
    elif max_price < 40_000_000:
        tier = "اقتصادی رو به متوسط"
    elif max_price <= 55_000_000:
        tier = "اقتصادی (در بازار فعلی میان‌رده‌ها معمولاً بالاترند)"
    elif max_price < 90_000_000:
        tier = "میان‌رده"
    else:
        tier = "میان‌رده تا بالارده"
    n = len([r for r in rows if r.get("price")])
    brand = intent.get("brand") or "محصول"
    mode = "پیشنهاد ارزش خرید" if intent.get("suggest_mode") else (
        "ارزان‌ترین‌ها" if intent.get("cheapest_mode") else "بهترین تطابق قیمت"
    )
    return (
        f"📌 در بودجه {max_price:,} تومان برای {brand}، بازه بازار فعلی بیشتر "
        f"«{tier}» است | حالت: {mode} | {n} گزینه قیمت‌دار"
    )


def _comparison_block(rows: list[dict], max_n: int = 3) -> list[str]:
    priced = [r for r in rows if r.get("price")]
    if len(priced) < 2:
        return []
    top = priced[:max_n]
    lines = ["", "📋 **مقایسه سریع گزینه‌های برتر**"]
    for i, r in enumerate(top, 1):
        title = str(r.get("title") or "")[:80]
        price = int(r["price"])
        src = r.get("source") or "وب"
        reg = " | رجیستری✅" if re.search(r"رجیستر", title, re.I) else ""
        lines.append(f"{i}. {title}")
        lines.append(f"   💰 {price:,} تومان | 🏪 {src}{reg}")
    return lines


def _ensure_multi_source(rows: list[dict], pool: list[dict], max_results: int) -> list[dict]:
    """اگر فقط یک منبع در خروجی است، از استخر نتایج منبع دوم اضافه کن."""
    if not rows:
        return rows
    sources = {str(r.get("source") or "وب") for r in rows}
    if len(sources) >= 2:
        return rows
    used = {r.get("url") for r in rows}
    primary = next(iter(sources))
    extras = [
        r for r in pool
        if r.get("url") not in used and str(r.get("source") or "وب") != primary
    ]
    extras.sort(key=lambda x: -float(x.get("_score", 0)))
    out = list(rows)
    for r in extras:
        out.append(r)
        if len(out) >= max_results:
            break
        if len({str(x.get("source") or "وب") for x in out}) >= 2:
            # یک مورد از منبع دوم کافی است؛ بقیه را هم تا سقف پر کن
            pass
    return out[:max_results]



def _digikala_product_url(item: dict) -> str:
    """ساخت URL معتبر محصول دیجی‌کالا از فیلدهای API (رشته یا dict)."""
    if not isinstance(item, dict):
        return ""
    pid = item.get("id") or item.get("product_id")

    def _from_value(val: Any) -> str:
        if val is None:
            return ""
        if isinstance(val, dict):
            uri = val.get("uri") or val.get("url") or val.get("path") or ""
            if isinstance(uri, str) and uri.strip():
                return uri.strip()
            return ""
        s = str(val).strip()
        # جلوگیری از str(dict)
        # str(dict) را پارس نکن؛ حالت dict بالاتر پوشش داده شده
        if s.startswith("{") and "uri" in s:
            return ""
        return s

    for key in ("url", "url_code", "page_url", "product_url"):
        link = _from_value(item.get(key))
        if link:
            break
    else:
        link = ""

    if not link and isinstance(item.get("default_variant"), dict):
        link = _from_value(item["default_variant"].get("url"))

    if link:
        if link.startswith("http"):
            return link.split("?")[0].rstrip("/") + "/"
        if not link.startswith("/"):
            link = "/" + link
        if "/product/" not in link and pid:
            link = f"/product/dkp-{pid}/"
        return "https://www.digikala.com" + link

    if pid:
        return f"https://www.digikala.com/product/dkp-{pid}/"
    return ""


async def _direct_digikala(query: str, max_price: int, limit: int) -> list[dict]:
    if _circuit_is_open("digikala"):
        return []

    async def _do() -> list[dict]:
        async with _SEARCH_SEM:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(11.0, connect=5.0),
                follow_redirects=True,
                headers={
                    "User-Agent": UA,
                    "Accept": "application/json",
                    "Accept-Language": "fa-IR,fa;q=0.9",
                },
            ) as client:
                params: dict[str, Any] = {"q": query, "page": 1}
                # دسته موبایل برای نتایج دقیق‌تر
                if any(k in query.lower() for k in ("گوشی", "موبایل", "شیائومی", "xiaomi", "سامسونگ", "آیفون", "iphone", "poco", "redmi")):
                    params["has_selling_stock"] = 1
                r = await client.get(
                    "https://api.digikala.com/v1/search/",
                    params=params,
                )
        if r.status_code >= 400:
            raise RuntimeError(f"digikala status {r.status_code}")
        data = r.json()
        raw = ((data.get("data") or {}).get("products") if isinstance(data, dict) else None)
        if not isinstance(raw, list):
            return []
        out: list[dict] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title_fa") or item.get("title") or "").strip()
            # استخراج قیمت از ساختارهای تو در توی API دیجی‌کالا
            rial = None
            for path in (
                lambda i: i.get("selling_price"),
                lambda i: i.get("price") if not isinstance(i.get("price"), dict) else None,
                lambda i: (i.get("price") or {}).get("selling_price") if isinstance(i.get("price"), dict) else None,
                lambda i: ((i.get("default_variant") or {}).get("price") or {}).get("selling_price"),
                lambda i: ((i.get("default_variant") or {}).get("price") or {}).get("rrp_price"),
                lambda i: (i.get("price") or {}).get("rrp_price") if isinstance(i.get("price"), dict) else None,
            ):
                try:
                    val = path(item)
                except Exception:
                    val = None
                rial = _parse_price(val)
                if rial:
                    break
            # API دیجی‌کالا معمولاً ریال می‌دهد
            price = (rial // 10) if rial else None
            price = _normalize_market_price(price, title) if price else None
            pid = item.get("id") or item.get("product_id")
            link = _digikala_product_url(item)
            status = str(
                item.get("status")
                or item.get("availability")
                or ((item.get("default_variant") or {}).get("status") if isinstance(item.get("default_variant"), dict) else "")
                or ""
            )
            avail = _normalize_availability(status)
            if not title or not price or not link or (max_price and price > max_price):
                continue
            # رد استوک مگر درخواست صریح
            if _is_used_listing(title) and not _wants_used(query):
                continue
            out.append(
                {
                    "title": title,
                    "url": link,
                    "price": price,
                    "seller": "دیجی‌کالا",
                    "source": "دیجی‌کالا",
                    "availability": avail,
                }
            )
            if len(out) >= limit:
                break
        if out:
            _STATS["direct_ok"] += 1
        return out

    result = await _with_retry(_do, source="digikala", max_attempts=4, base_delay=0.8)
    rows = result if isinstance(result, list) else []
    if not rows:
        rows = await _digikala_html_fallback(query, max_price, limit)
    return rows


async def _direct_site_search(query: str, domain: str, limit: int) -> list[dict]:
    if _circuit_is_open(domain):
        return []
    template = _SOURCE_SEARCH_URLS.get(domain)
    if not template:
        return []

    async def _do() -> list[dict]:
        url = template.format(q=quote_plus(query))
        async with _SEARCH_SEM:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(10.0, connect=4.0),
                follow_redirects=True,
                headers={"User-Agent": UA, "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.7"},
            ) as client:
                r = await client.get(url)
        if r.status_code >= 400:
            raise RuntimeError(f"{domain} status {r.status_code}")
        soup = BeautifulSoup(r.text, "html.parser")
        out = _jsonld_products(soup, domain, limit)
        if not out:
            intent = _shopping_intent(query)
            for a in soup.select("a[href]")[:250]:
                title = " ".join(a.get_text(" ", strip=True).split())
                if len(title) < 8 or not _shopping_product_match(
                    {"title": title, "snippet": ""}, query, intent
                ):
                    continue
                href = str(a.get("href") or "").strip()
                if href.startswith("/"):
                    href = f"https://{domain}{href}"
                if not href.startswith("http") or domain not in urlparse(href).netloc:
                    continue
                parent = a.parent.get_text(" ", strip=True) if a.parent else ""
                price = _price_from_text(parent)
                if price:
                    out.append(
                        {
                            "title": title[:240],
                            "url": href,
                            "price": price,
                            "seller": IRAN_SITES.get(domain, ""),
                            "source": IRAN_SITES.get(domain, domain),
                            "availability": "",
                        }
                    )
                if len(out) >= limit:
                    break
        if out:
            _STATS["direct_ok"] += 1
        return out[:limit]

    result = await _with_retry(_do, source=domain, max_attempts=2)
    return result if isinstance(result, list) else []


# ---------------------------------------------------------------------------
# Ranking & diversification
# ---------------------------------------------------------------------------
def _query_variants(query: str, budget: int) -> list[str]:
    q = _clean_query(query)
    variants = [q]
    intent = _shopping_intent(query)
    if budget:
        variants += [f"{q} تا {budget:,} تومان", f"{q} قیمت خرید", f"{q} فروشگاه"]
        # برای بودجه متوسط/بالا مدل‌های میان‌رده و بالارده را هم جستجو کن
        # تا API فقط ارزان‌ترین‌ها را برنگرداند.
        if intent.get("phone") and budget >= 8_000_000:
            brand = (intent.get("brand") or "").lower()
            if brand in ("شیائومی", "xiaomi", "پوکو", "poco") or "شیائومی" in q or "xiaomi" in q.lower():
                if budget >= 30_000_000:
                    variants += [
                        "شیائومی 13T Pro",
                        "Xiaomi 14",
                        "Poco F6 Pro",
                        "Redmi Note 13 Pro",
                    ]
                elif budget >= 15_000_000:
                    variants += [
                        "Redmi Note 13",
                        "Poco X6",
                        "شیائومی 13T",
                    ]
                else:
                    variants += ["Redmi Note 12", "Poco X5"]
            elif brand in ("سامسونگ", "samsung") or "سامسونگ" in q:
                if budget >= 30_000_000:
                    variants += ["Galaxy A55", "Galaxy S23 FE", "Galaxy A35"]
                else:
                    variants += ["Galaxy A25", "Galaxy A15"]
            elif brand in ("اپل", "apple", "آیفون") or "آیفون" in q or "iphone" in q.lower():
                variants += ["iPhone 13", "iPhone 14", "آیفون ۱۳"]
    else:
        variants += [f"{q} قیمت", f"{q} خرید", f"{q} فروشگاه"]
    out: list[str] = []
    seen: set[str] = set()
    for x in variants:
        x = " ".join(x.split())
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out[:6]


def _rank(rows: list[dict], query: str, max_price: int) -> list[dict]:
    intent = _shopping_intent(query)
    seen_urls: set[str] = set()
    best_by_model_source: dict[tuple[str, str], dict] = {}
    out: list[dict] = []
    for x in rows:
        url = str(x.get("url") or "").strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        title = str(x.get("title") or "")
        price = x.get("price")
        if not _shopping_product_match(x, query, intent):
            continue
        if max_price and price and int(price) > int(max_price):
            continue
        # ترجیح موجود بودن
        avail = str(x.get("availability") or "")
        if avail == "ناموجود":
            continue
        rel = _relevance(title, query)
        if (
            rel < 15
            and not (
                intent.get("phone")
                and intent.get("brand")
                and _shopping_brand_match(title, intent.get("brand"))
            )
        ):
            continue
        model = _shopping_model_key(title)
        src = str(x.get("source") or "وب")
        trust = TRUST.get(src, 60)
        score = (
            rel
            + trust * 0.18
            + (18 if price and max_price and price <= max_price else 5 if price else 0)
        )
        if x.get("_verified_direct"):
            score += 8
        if avail == "موجود":
            score += 4
        # برای بودجه بالا: ترجیح بازه معقول (نه فقط ارزان‌ترین)
        # اگر کاربر سقف ۵۰ میلیون گذاشته، مدل ۳ میلیونی «بهترین» نیست.
        if price and max_price and max_price >= 8_000_000:
            ratio = float(price) / float(max_price)
            if intent.get("cheapest_mode"):
                score += max(0, 20 * (1.0 - ratio))
            elif 0.25 <= ratio <= 0.95:
                score += 22
            elif 0.12 <= ratio < 0.25:
                score += 8
            elif ratio < 0.08:
                score -= 12
            low = title.lower()
            if price < 6_000_000 and any(
                k in low for k in ("13t pro", "14 pro", "14 ultra", "s23", "s24", "iphone 14", "iphone 15")
            ):
                score -= 25
        # Value score + رجیستری
        score += _value_score(
            {"title": title, "price": price, "source": src,
             "_verified_direct": x.get("_verified_direct"),
             "_cross_validated": x.get("_cross_validated")},
            max_price,
            intent,
        )
        x["_score"] = score
        x["_model_key"] = model
        if model:
            k = (model, src)
            prev = best_by_model_source.get(k)
            if prev is None or (
                bool(x.get("_verified_direct")),
                -(int(price or 10**30)),
                float(score),
            ) > (
                bool(prev.get("_verified_direct")),
                -(int(prev.get("price") or 10**30)),
                float(prev.get("_score", 0)),
            ):
                best_by_model_source[k] = x
        else:
            out.append(x)
    out.extend(best_by_model_source.values())
    # با بودجه بالا اول امتیاز، بعد نزدیکی به میانه بودجه؛ وگرنه ارزان‌تر
    if max_price and max_price >= 8_000_000:
        target = max_price * 0.55

        def _sort_key(x):
            p = x.get("price") or 0
            return (-float(x.get("_score", 0)), abs(p - target), p)

        out.sort(key=_sort_key)
    else:
        out.sort(key=lambda x: (-float(x.get("_score", 0)), x.get("price") or 10**30))
    return out


def _diversify_shopping_rows(
    rows: list[dict], max_results: int = 10, max_per_source: int = 2
) -> list[dict]:
    """نتایج را با اولویت دیجی‌کالا، سپس ترب، سپس بقیه پخش می‌کند."""
    if not rows:
        return []
    priority = {"دیجی‌کالا": 0, "ترب": 1}

    def _src_rank(row: dict) -> tuple:
        src = str(row.get("source") or "وب")
        return (priority.get(src, 50), -float(row.get("_score", 0)))

    ordered = sorted(rows, key=_src_rank)
    result: list[dict] = []
    counts: dict[str, int] = {}
    used_urls: set[str] = set()
    # دور اول: حداقل یکی از هر منبع (با اولویت دیجی‌کالا)
    for row in ordered:
        url = str(row.get("url") or "").strip()
        src = str(row.get("source") or "وب")
        if not url or url in used_urls or counts.get(src, 0) >= 1:
            continue
        used_urls.add(url)
        counts[src] = counts.get(src, 0) + 1
        result.append(row)
        if len(result) >= max_results:
            return result
    # دور دوم: پر کردن ظرفیت با اولویت همان ترتیب
    for row in ordered:
        url = str(row.get("url") or "").strip()
        src = str(row.get("source") or "وب")
        if not url or url in used_urls or counts.get(src, 0) >= max_per_source:
            continue
        used_urls.add(url)
        counts[src] = counts.get(src, 0) + 1
        result.append(row)
        if len(result) >= max_results:
            return result
    return result


# ---------------------------------------------------------------------------
# History & alerts
# ---------------------------------------------------------------------------
def _save_history_rows(rows: list[dict]) -> None:
    try:
        from bot.database import get_db_connection

        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS shopping_price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_key TEXT,
                title TEXT,
                source TEXT,
                url TEXT,
                price INTEGER,
                captured_at TEXT DEFAULT (datetime('now'))
            )
            """
        )
        for x in rows:
            if not x.get("price") or not x.get("_verified_direct"):
                continue
            key = hashlib.sha1(
                re.sub(r"\s+", " ", str(x.get("title") or "").lower()).encode(
                    "utf-8", "ignore"
                )
            ).hexdigest()[:24]
            c.execute(
                "INSERT INTO shopping_price_history(product_key,title,source,url,price) "
                "VALUES(?,?,?,?,?)",
                (
                    key,
                    str(x.get("title") or "")[:220],
                    str(x.get("source") or "")[:80],
                    str(x.get("url") or "")[:1000],
                    int(x["price"]),
                ),
            )
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.debug("shopping history save failed: %s", exc)


def _history_summary(query: str, days: int = 30) -> tuple[str, dict]:
    try:
        from bot.database import get_db_connection

        conn = get_db_connection()
        rows = conn.execute(
            "SELECT title,source,price,captured_at,url FROM shopping_price_history "
            "WHERE captured_at >= datetime('now', ?) ORDER BY id DESC LIMIT 5000",
            (f"-{max(1, int(days))} days",),
        ).fetchall()
        conn.close()
        intent = _shopping_intent(query)
        budget = _budget(query)
        target_model_tokens = set(_shopping_model_key(_clean_query(query)).split())
        matched = []
        for r in rows:
            title = str(r[0] or "")
            price = int(r[2] or 0)
            if not _shopping_product_match({"title": title, "snippet": ""}, query, intent):
                continue
            if budget and (not price or price > budget):
                continue
            if target_model_tokens:
                tt = set(_shopping_model_key(title).split())
                if len(target_model_tokens & tt) < max(1, min(2, len(target_model_tokens))):
                    continue
            matched.append(r)
        prices = [int(r[2]) for r in matched if r[2]]
        if not prices:
            return "", {}
        stats = {
            "min": min(prices),
            "max": max(prices),
            "avg": int(sum(prices) / len(prices)),
            "count": len(prices),
        }
        return (
            f"📈 تاریخچه مرتبط: کمینه {stats['min']:,} | بیشینه {stats['max']:,} | "
            f"میانگین {stats['avg']:,} تومان در {days} روز اخیر",
            stats,
        )
    except Exception:
        return "", {}


def shopping_price_history(query: str = "", days: int = 30, user_id: int = 0) -> str:
    query = str(query or "").strip()
    if not query:
        return "نام محصول برای تاریخچه قیمت مشخص نیست."
    try:
        from bot.database import get_db_connection

        conn = get_db_connection()
        rows = conn.execute(
            "SELECT title,source,price,captured_at,url FROM shopping_price_history "
            "WHERE captured_at >= datetime('now', ?) ORDER BY id DESC LIMIT 3000",
            (f"-{max(1, int(days))} days",),
        ).fetchall()
        conn.close()
        qt = _tokens(query)
        matched = (
            [r for r in rows if len(qt & _tokens(r[0])) >= max(1, len(qt) // 2)]
            if qt
            else []
        )
        if not matched:
            return f"برای «{query}» هنوز تاریخچه قیمت کافی ثبت نشده است."
        prices = [int(r[2]) for r in matched if r[2]]
        lines = [
            f"📈 **تاریخچه قیمت — {query}**",
            f"🗓 بازه: {days} روز | مشاهدات: {len(prices)}",
        ]
        if prices:
            lines.append(
                f"💰 کمینه: {min(prices):,} | بیشینه: {max(prices):,} | "
                f"میانگین: {sum(prices) // len(prices):,} تومان"
            )
            if len(prices) >= 2:
                change = prices[0] - prices[-1]
                pct = (change / prices[-1] * 100) if prices[-1] else 0
                lines.append(f"📊 تغییر مشاهده‌شده: {change:+,} تومان ({pct:+.1f}%)")
        for r in matched[:10]:
            lines.append(f"• {r[3]} | {r[1]} | {int(r[2]):,} تومان")
        return "\n".join(lines)
    except Exception as exc:
        return f"تاریخچه قیمت در دسترس نیست: {exp}"


def _create_alert(user_id: int, query: str, target: int, direction: str = "below") -> str:
    try:
        from bot.database import get_db_connection

        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS shopping_price_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                query TEXT NOT NULL,
                target INTEGER NOT NULL,
                direction TEXT NOT NULL DEFAULT 'below',
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_price INTEGER,
                last_checked TEXT,
                triggered_at TEXT
            )
            """
        )
        cur = c.execute(
            "INSERT INTO shopping_price_alerts(user_id,query,target,direction) VALUES(?,?,?,?)",
            (int(user_id), query[:300], int(target), direction),
        )
        conn.commit()
        aid = cur.lastrowid
        conn.close()
        return (
            f"🔔 هشدار قیمت #{aid} ثبت شد.\n"
            f"اگر «{query}» به {target:,} تومان یا کمتر برسد، بهت پیام می‌دهم."
        )
    except Exception as exc:
        return f"ثبت هشدار ناموفق بود: {exp}"


def create_shopping_price_alert(user_id: int, query: str, target: int) -> str:
    if not user_id or not query or int(target or 0) <= 0:
        return "نام محصول، کاربر و قیمت هدف لازم است."
    return _create_alert(user_id, _clean_query(query), int(target), "below")


def list_shopping_price_alerts(user_id: int) -> str:
    try:
        from bot.database import get_db_connection

        conn = get_db_connection()
        rows = conn.execute(
            "SELECT id,query,target,active,created_at,last_price "
            "FROM shopping_price_alerts WHERE user_id=? ORDER BY id DESC",
            (int(user_id),),
        ).fetchall()
        conn.close()
        if not rows:
            return "🔔 هشدار خرید فعالی نداری."
        lines = ["🔔 هشدارهای قیمت خرید:"]
        for r in rows:
            lines.append(
                f"#{r[0]} | {'فعال' if r[3] else 'غیرفعال'} | {r[1]} | "
                f"هدف {int(r[2]):,} تومان"
            )
        return "\n".join(lines)
    except Exception as exc:
        return f"هشدارها در دسترس نیستند: {exp}"


def cancel_shopping_price_alert(user_id: int, alert_id: int) -> str:
    try:
        from bot.database import get_db_connection

        conn = get_db_connection()
        cur = conn.execute(
            "UPDATE shopping_price_alerts SET active=0 WHERE id=? AND user_id=?",
            (int(alert_id), int(user_id)),
        )
        conn.commit()
        conn.close()
        return "✅ هشدار غیرفعال شد." if cur.rowcount else "هشدار پیدا نشد."
    except Exception as exc:
        return f"لغو هشدار ناموفق بود: {exp}"


def shopping_engine_status() -> str:
    open_circuits = [k for k, (f, until) in _CIRCUIT.items() if time.time() < until]
    return (
        "🛒 Shopping Engine v3.2\n"
        + " | ".join(f"{k}={v}" for k, v in _STATS.items())
        + f" | cache={len(_CACHE)}"
        + f" | circuits_open={open_circuits or 'none'}"
        + f" | redis={'yes' if _REDIS else 'no'}"
    )


# ---------------------------------------------------------------------------
# Optional external guide (mobo.news)
# ---------------------------------------------------------------------------
async def _mobo_phone_guide(query: str) -> set[str]:
    try:
        async with _SEARCH_SEM:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(10.0, connect=4.0),
                follow_redirects=True,
                headers={"User-Agent": UA, "Accept-Language": "fa-IR,fa;q=0.9"},
            ) as client:
                r = await client.get("https://mobo.news/best-priced-phone-guide/")
        if r.status_code >= 400:
            return set()
        soup = BeautifulSoup(r.text, "html.parser")
        out: set[str] = set()
        for node in soup.select("h2,h3,h4,p,li"):
            t = " ".join(node.get_text(" ", strip=True).split())
            if len(t) < 5:
                continue
            if any(
                k in t.lower()
                for k in (
                    "شیائومی", "xiaomi", "redmi", "poco", "پوکو", "ردمی",
                    "سامسونگ", "samsung", "iphone", "آیفون",
                )
            ):
                out.add(_shopping_model_key(t))
        return {x for x in out if x}
    except Exception as exc:
        logger.debug("mobo guide failed: %s", exc)
        return set()


# ---------------------------------------------------------------------------
# Main public API
# ---------------------------------------------------------------------------
async def search_shopping(
    query: str = "",
    source: str = "all",
    max_results: int = 10,
    min_price: int = 0,
    max_price: int = 0,
    user_id: int = 0,
) -> str:
    """موتور خرید نهایی v3.1: چندمنبعی، فیلتر معنایی، تأیید صفحه، retry و circuit breaker."""
    raw = " ".join(str(query or "").split()).strip()
    if not raw:
        return "عبارت محصول برای جستجو مشخص نیست."

    _STATS["searches"] += 1
    max_results = max(4, min(int(max_results or 10), 12))
    budget = _budget(raw)
    if budget and not max_price:
        max_price = budget
    foreign = _foreign_requested(raw)
    domain = _explicit_domain(raw)
    if domain and domain not in IRAN_SITES:
        foreign = True
    clean = _clean_query(raw)
    if not clean or len(clean) < 2:
        clean = raw
    intent = _shopping_intent(raw)

    key = _cache_key(clean, domain or source, max_price, foreign) + ":v31"
    cached = await _cache_get(key)
    if cached is not None:
        rows = cached
    else:
        variants = _query_variants(clean, budget)
        if intent.get("brand"):
            brand_words = {
                "شیائومی": "شیائومی Xiaomi Redmi Poco",
                "xiaomi": "Xiaomi Redmi Poco شیائومی",
                "سامسونگ": "سامسونگ Samsung Galaxy",
                "samsung": "Samsung Galaxy سامسونگ",
                "اپل": "Apple iPhone اپل آیفون",
                "apple": "Apple iPhone اپل آیفون",
                "آنر": "Honor آنر",
                "honor": "Honor آنر",
                "پوکو": "Poco پوکو Xiaomi",
                "poco": "Poco پوکو Xiaomi",
            }.get(intent["brand"], intent["brand"])
            variants = [f"{v} {brand_words}" for v in variants[:3]]
        if intent.get("touch"):
            variants = [f"{v} گوشی هوشمند لمسی Android smartphone" for v in variants[:3]]

        if domain:
            domains = [domain]
        elif foreign:
            domains = ["amazon.com", "ebay.com", "walmart.com", "aliexpress.com", ""]
        elif source not in ("all", "همه", "تمام", "everywhere", "web", ""):
            requested = [x for x in source.replace(",", " ").split() if x in SOURCES]
            domains = [
                SOURCES[x]["domains"][0]
                for x in requested
                if SOURCES[x].get("domains")
            ]
            if not domains:
                domains = [
                    "digikala.com", "torob.com", "technolife.ir",
                    "snappshop.ir", "emalls.ir",
                ]
        else:
            domains = [
                "digikala.com", "torob.com", "technolife.ir", "snappshop.ir",
                "emalls.ir", "meghdadit.com", "kalaoma.com", "19kala.com", "mobile.ir",
            ]

        rows: list[dict] = []

        # Direct API (highest confidence)
        if not foreign and not domain:
            direct_tasks = []
            for v in variants[:2]:
                direct_tasks += [
                    _direct_digikala(v, max_price, max(8, max_results)),
                    _direct_torob(v, max_price, max(8, max_results)),
                ]
            direct_batches = await asyncio.gather(*direct_tasks, return_exceptions=True)
            for b in direct_batches:
                if isinstance(b, list):
                    for x in b:
                        x["_verified_direct"] = True
                        rows.append(x)

        # Direct site pages
        direct_site_tasks = []
        for v in variants[:2]:
            for d in domains:
                if not foreign and d in _SOURCE_SEARCH_URLS:
                    direct_site_tasks.append(
                        _direct_site_search(v, d, max(6, max_results // 2 + 3))
                    )
        direct_site_batches = (
            await asyncio.gather(*direct_site_tasks, return_exceptions=True)
            if direct_site_tasks
            else []
        )
        for b in direct_site_batches:
            if isinstance(b, list):
                for x in b:
                    x["_verified_direct"] = bool(x.get("price"))
                    if _shopping_product_match(x, raw, intent):
                        rows.append(x)

        # Search-engine fallback
        search_tasks = []
        for v in variants[:2]:
            for d in domains:
                search_tasks.append(
                    _fetch_source(v, d, max(6, max_results // 2 + 3), foreign)
                )
        search_batches = (
            await asyncio.gather(*search_tasks, return_exceptions=True)
            if search_tasks
            else []
        )
        for b in search_batches:
            if isinstance(b, list):
                for x in b:
                    if _shopping_product_match(x, raw, intent):
                        x.setdefault("_verified_direct", False)
                        rows.append(x)

        # Pre-filter
        filtered: list[dict] = []
        seen_urls: set[str] = set()
        for x in rows:
            title = str(x.get("title") or "")
            if not title or not _shopping_product_match(x, raw, intent):
                continue
            p = x.get("price")
            if p and max_price and p > max_price:
                continue
            if min_price and (not p or p < min_price):
                continue
            if str(x.get("availability") or "") == "ناموجود":
                continue
            u = str(x.get("url") or "").strip()
            if not u or u in seen_urls:
                continue
            seen_urls.add(u)
            filtered.append(x)

        # حذف قیمت‌های پرت (مثلاً ÷۱۰ اشتباه از ترب)
        filtered = _filter_price_outliers(filtered)
        rows = _rank(filtered, clean, max_price)
        # اعتبارسنجی متقابل قیمت بین منابع
        rows = _cross_validate_prices(rows)

        # mobo.news boost
        mobo_models = await _mobo_phone_guide(raw) if intent.get("phone") else set()
        if mobo_models:
            for x in rows:
                mk = _shopping_model_key(x.get("title", ""))
                if mk and any(
                    mk == mm or len(set(mk.split()) & set(mm.split())) >= 2
                    for mm in mobo_models
                ):
                    x["_mobo_match"] = True
                    x["_score"] = float(x.get("_score", 0)) + 18

        # Inspect top non-verified pages (controlled concurrency)
        inspect_candidates = []
        for x in rows:
            if x.get("_verified_direct"):
                continue
            inspect_candidates.append(x)
            if len(inspect_candidates) >= 14:
                break
        if inspect_candidates:
            checked = await asyncio.gather(
                *[
                    _inspect(x["url"], x.get("title", ""), x.get("snippet", ""))
                    for x in inspect_candidates
                ],
                return_exceptions=True,
            )
            by_url = {str(x.get("url")): x for x in rows}
            for obj in checked:
                if isinstance(obj, ProductResult):
                    old = by_url.get(obj.url)
                    if old is not None:
                        old["title"] = obj.title or old.get("title")
                        if obj.price:
                            old["price"] = _normalize_market_price(obj.price, obj.title or old.get("title", ""))
                        old["seller"] = obj.seller or old.get("seller", "")
                        old["availability"] = obj.availability or old.get("availability", "")
                        old["_verified_direct"] = bool(old.get("price"))
                        if obj.source and obj.source != "general":
                            old["source"] = SOURCES.get(
                                obj.source, {"label": obj.source}
                            ).get("label", obj.source)

        # Final filter
        final: list[dict] = []
        for x in rows:
            if not _shopping_product_match(x, raw, intent):
                continue
            p = x.get("price")
            if not p and max_price:
                continue
            if p and max_price and p > max_price:
                continue
            if min_price and (not p or p < min_price):
                continue
            if str(x.get("availability") or "") == "ناموجود":
                continue
            final.append(x)

        final.sort(
            key=lambda x: (-float(x.get("_score", 0)), x.get("price") or 10**30)
        )
        rows = _diversify_shopping_rows(
            final, max_results=max_results, max_per_source=2
        )
        # تضمین حداقل دو منبع در صورت امکان
        rows = _ensure_multi_source(rows, final, max_results)
        distinct_sources = {str(x.get("source") or "وب") for x in final}
        if len(distinct_sources) <= 1 and len(rows) < min(max_results, len(final)):
            used = {x.get("url") for x in rows}
            for x in final:
                if x.get("url") not in used:
                    rows.append(x)
                    used.add(x.get("url"))
                if len(rows) >= max_results:
                    break

        await _cache_set(key, rows)
        if rows:
            _save_history_rows(rows)

    if not rows:
        _STATS["empty"] += 1
        return (
            f"⚠️ برای «{clean}» با این مشخصات نتیجه قابل‌اعتماد و داخل بودجه "
            "از منابع زنده پیدا نشد؛ قیمت حدسی ارائه نمی‌کنم."
        )

    priced = [x for x in rows if x.get("price")]
    market = "بازار جهانی" if foreign else "بازار ایران"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    source_counts: dict[str, int] = {}
    for x in rows:
        src = str(x.get("source") or "وب")
        source_counts[src] = source_counts.get(src, 0) + 1
    unique_sources = len(source_counts)

    profile = _budget_profile_line(max_price, intent, rows)
    lines = [
        f"🛒 **نتایج خرید چندفروشگاهی — {raw}**",
        f"🌍 {market} | 🕒 {now}",
        f"🔎 منابع دارای نتیجه معتبر: {', '.join(source_counts.keys())}",
    ]
    if profile:
        lines.append(profile)
    if max_price:
        brand_label = (
            "شیائومی"
            if intent.get("brand") in ("شیائومی", "xiaomi")
            else intent.get("brand") or "بدون برند"
        )
        product_label = (
            "گوشی لمسی/هوشمند"
            if intent.get("touch")
            else "گوشی"
            if intent.get("phone")
            else "محصول"
        )
        lines.append(
            f"🧩 فیلتر هوشمند: {brand_label} | {product_label} | "
            f"سقف {max_price:,} تومان"
        )
    else:
        lines.append("🧩 فیلتر هوشمند محصول و برند فعال است.")
    lines += [
        "ℹ️ ✅ فقط قیمت‌هایی که از کاتالوگ/API یا صفحه محصول قابل‌استخراج و تأیید "
        "بوده‌اند با نشان تأیید نمایش داده می‌شوند.",
        "",
    ]

    for i, x in enumerate(rows, 1):
        price = x.get("price")
        src = x.get("source") or "وب"
        verified = " ✅" if x.get("_verified_direct") else ""
        avail = x.get("availability") or ""
        lines.append(f"**{i}. {x.get('title') or 'محصول'}**")
        if price and not foreign:
            lines.append(f"🏪 {src}{verified} | 💰 {price:,} تومان")
        elif price:
            lines.append(f"🏪 {src}{verified} | 💰 {price:,}")
        else:
            lines.append(f"🏪 {src} | 💰 قیمت قابل‌تأیید نیست")
        if x.get("seller"):
            lines.append(f"👤 {x['seller']}")
        if avail:
            lines.append(f"📦 {avail}")
        lines.append(f"🔗 {x['url']}")
        lines.append("")

    if priced:
        cheapest = min(priced, key=lambda x: x["price"])
        verified_priced = [x for x in priced if x.get("_verified_direct")]
        verified_cheapest = (
            min(verified_priced, key=lambda x: x["price"]) if verified_priced else None
        )
        lines.append(
            f"🏆 **ارزان‌ترین گزینه داخل بودجه:** {cheapest['price']:,} تومان — "
            f"{cheapest.get('source') or 'وب'}"
        )
        if verified_cheapest:
            lines.append(
                f"🔐 **ارزان‌ترین قیمت تأییدشده از صفحه:** "
                f"{verified_cheapest['price']:,} تومان — "
                f"{verified_cheapest.get('source') or 'وب'}"
            )
        if max_price:
            inside = len([x for x in priced if x["price"] <= max_price])
            lines.append(f"🎯 {inside} نتیجه داخل بودجه {max_price:,} تومان قرار گرفت.")

    if source_counts:
        lines.append(
            "📊 **پوشش منابع:** "
            + " · ".join(
                f"{k}: {v}" for k, v in sorted(source_counts.items(), key=lambda z: -z[1])
            )
        )

    candidates = [x for x in priced if not max_price or x["price"] <= max_price]
    if candidates:
        for x in candidates:
            src = x.get("source") or "وب"
            band = 0.0
            p = x.get("price")
            if p and max_price and max_price >= 8_000_000:
                ratio = float(p) / float(max_price)
                if 0.25 <= ratio <= 0.95:
                    band = 20.0
                elif ratio < 0.08:
                    band = -15.0
            x["_final_score"] = (
                float(x.get("_score", 0))
                + TRUST.get(src, 60) * 0.12
                + (8 if x.get("_verified_direct") else 0)
                + band
            )
        best = max(candidates, key=lambda x: x["_final_score"])
        model_key = _shopping_model_key(best.get("title"))
        same_model = [
            x
            for x in candidates
            if _shopping_model_key(x.get("title")) == model_key and model_key
        ]
        lines += _comparison_block(rows, 3)
        lines += [
            "",
            "🧠 **بررسی نهایی**",
            f"• 🎯 بهترین تطابق: **{best.get('title') or 'محصول'}** — "
            f"{best.get('price', 0):,} تومان از {best.get('source') or 'وب'}",
        ]
        if same_model:
            model_prices = sorted({int(x["price"]) for x in same_model if x.get("price")})
            if model_prices:
                lines.append(
                    f"• 📊 همین مدل در {len({x.get('source') for x in same_model})} منبع پیدا شد؛ "
                    f"بازه قیمت: {model_prices[0]:,} تا {model_prices[-1]:,} تومان"
                )
        if unique_sources >= 2:
            lines.append(
                f"• ✅ مقایسه واقعی چندفروشگاهی: {unique_sources} منبع در خروجی حضور دارند."
            )
        mobo_hits = sum(1 for x in candidates if x.get("_mobo_match"))
        if mobo_hits:
            lines.append(
                f"• 🧠 موبونیوز: {mobo_hits} مدل با راهنمای بهترین گوشی‌های "
                "بازه‌های قیمتی تطابق داشتند."
            )
        else:
            lines.append(
                "• 🧠 موبونیوز بررسی شد؛ تطابق کافی با مدل‌های نتیجه فعلی پیدا نشد."
            )
        if max_price:
            lines.append(f"• 💰 فاصله تا سقف بودجه: {max_price - best['price']:,} تومان")
        lines.append(
            "• ⚠️ قبل از خرید، گارانتی، رجیستری، موجودی و قیمت نهایی همان فروشنده را "
            "دوباره بررسی کن."
        )

    hist, _ = _history_summary(raw, 30)
    if hist:
        lines.extend(["", hist])
    lines += ["", "⚠️ قیمت و موجودی لحظه‌ای هستند و ممکن است تغییر کنند."]
    return "\n".join(lines)


async def check_shopping_price_alerts(context) -> None:
    """Low-frequency background check for user shopping alerts."""
    try:
        from bot.database import get_db_connection

        conn = get_db_connection()
        rows = conn.execute(
            "SELECT id,user_id,query,target,direction FROM shopping_price_alerts "
            "WHERE active=1 ORDER BY id LIMIT 25"
        ).fetchall()
        conn.close()
        for aid, uid, q, target, direction in rows:
            try:
                result = await search_shopping(q, max_results=3, user_id=int(uid))
                prices = [
                    int(x)
                    for x in re.findall(r"(?:💰\s*|🏆[^\n]*?\*\*)\s*([0-9,]+)", result)
                    if x
                ]
                if not prices:
                    continue
                value = min(prices)
                conn = get_db_connection()
                conn.execute(
                    "UPDATE shopping_price_alerts SET last_price=?, last_checked=CURRENT_TIMESTAMP "
                    "WHERE id=?",
                    (value, aid),
                )
                conn.commit()
                conn.close()
                hit = (value <= int(target)) if direction == "below" else (value >= int(target))
                if hit:
                    conn = get_db_connection()
                    conn.execute(
                        "UPDATE shopping_price_alerts SET active=0, triggered_at=CURRENT_TIMESTAMP "
                        "WHERE id=?",
                        (aid,),
                    )
                    conn.commit()
                    conn.close()
                    await context.bot.send_message(
                        chat_id=int(uid),
                        text=(
                            f"🔔 هشدار قیمت\n\n«{q}»\n"
                            f"قیمت مشاهده‌شده: {value:,} تومان\n"
                            f"هدف: {int(target):,} تومان\n\n"
                            "برای بررسی دوباره، جستجوی خرید را اجرا کن."
                        ),
                    )
            except Exception as exc:
                logger.debug("shopping alert %s failed: %s", aid, exc)
    except Exception as exc:
        logger.debug("shopping alerts job failed: %s", exc)
