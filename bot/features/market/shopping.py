"""هوش خرید بازار — Shopping Engine v3 (نسخه یکپارچه و تمیز)

جستجوی زنده و چندفروشگاهی قیمت محصول در بازار ایران (پیش‌فرض)
+ اینستاگرام + در صورت درخواست کاربر، منابع خارجی.

قوانین:
- بازار ایران پیش‌فرض است؛ منابع خارجی فقط با درخواست صریح فعال می‌شوند.
- قیمت حدسی ارائه نمی‌شود؛ فقط قیمت استخراج‌شده از API یا صفحه محصول.
- هیچ وابستگی اجباری به AI ندارد.
- تاریخچه قیمت و هشدار قیمت پشتیبانی می‌شود.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
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
# Constants
# ---------------------------------------------------------------------------
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36 RoozeZiba/5.0"
)
CACHE_TTL = 180
_CACHE: dict[str, tuple[float, list[dict]]] = {}
_STATS = {
    "searches": 0,
    "cache_hits": 0,
    "direct_ok": 0,
    "web_ok": 0,
    "empty": 0,
    "errors": 0,
}
_SEARCH_SEM = asyncio.Semaphore(8)

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
    "ترب": 100,
    "دیجی‌کالا": 98,
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
# Intent / product matching (especially strong for phones)
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
    # «نه گوشی لمسی» معمولاً اصلاح پیام قبلی است
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
    return {
        "phone": phone,
        "touch": touch and not non_touch,
        "non_touch": non_touch,
        "brand": brand,
    }


def _shopping_brand_match(text: str, brand: str) -> bool:
    if not brand:
        return True
    low = str(text or "").lower()
    words = _BRAND_WORDS.get(brand, {brand})
    return any(w.lower() in low for w in words)


def _shopping_product_match(row: dict, query: str, intent: dict) -> bool:
    title = str(row.get("title") or "")
    snippet = str(row.get("snippet") or "")
    text = f"{title} {snippet}".lower()
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
    """کلید نسبتاً پایدار برای یکی‌کردن یک مدل در فروشگاه‌های مختلف."""
    t = str(title or "").lower().replace("ي", "ی").replace("ك", "ک")
    t = re.sub(
        r"\b(گوشی|موبایل|mobile|phone|smartphone|شیائومی|xiaomi|سامسونگ|samsung)\b",
        " ",
        t,
    )
    t = re.sub(r"\b\d+\s*(?:gb|گیگ|گیگابایت|گیک|مگابایت|mb|گ)\b", " ", t, flags=re.I)
    t = re.sub(r"\b(?:رم|ram)\s*\d+\b", " ", t, flags=re.I)
    t = re.sub(r"\b(?:دو|2)\s*سیم(?:کارت)?\b", " ", t, flags=re.I)
    t = re.sub(r"\b(?:حافظه|storage)\s*\d+\s*(?:gb|گیگ|گیگابایت|mb|مگابایت)?\b", " ", t, flags=re.I)
    t = re.sub(r"[^\wآ-ی]+", " ", t)
    stop = {
        "مدل", "ظرفیت", "حافظه", "داخلی", "نسخه", "رجیستر", "رجیستری",
        "تومان", "با", "و", "برای", "مشکی", "سفید", "آبی", "سبز",
        "صورتی", "خاکستری", "رم", "ram", "رنگ",
    }
    toks = [x for x in t.split() if x not in stop and len(x) >= 2]
    return " ".join(toks[:12])


# ---------------------------------------------------------------------------
# JSON-LD extraction
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
    availability = str(offers.get("availability") or "").split("/")[-1]
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
                    "availability": (
                        str(offers.get("availability", "")).split("/")[-1]
                        if isinstance(offers, dict)
                        else ""
                    ),
                }
            )
            if len(out) >= limit:
                return out
    return out


# ---------------------------------------------------------------------------
# Page inspection (used for non-direct results)
# ---------------------------------------------------------------------------
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

    try:
        async with httpx.AsyncClient(
            timeout=15.0, follow_redirects=True, headers={"User-Agent": UA}
        ) as client:
            r = await client.get(url)
            if r.status_code >= 400:
                return result
            soup = BeautifulSoup(r.text, "html.parser")

            # JSON-LD first
            for obj in _extract_jsonld(soup):
                typ = obj.get("@type")
                if typ == "Product" or (isinstance(typ, list) and "Product" in typ):
                    p, old, seller, avail, image, cur = _from_product(obj)
                    if p is not None:
                        result.price = p
                    if old is not None and (result.price is None or old > result.price):
                        result.old_price = old
                    result.seller = seller or result.seller
                    result.availability = avail
                    result.image = image
                    result.currency = cur
                    if result.price is not None:
                        break

            # Meta tags
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

            # Persian text patterns
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
                        result.price, result.currency = _currency_and_price(m.group(1), "تومان")
                        break

            # Better title from og:title
            og_title = soup.select_one('meta[property="og:title"]')
            if og_title and og_title.get("content"):
                clean = _clean_title(og_title["content"])
                if len(clean) > 8:
                    result.title = clean

    except Exception as exc:
        logger.debug("shopping inspect failed %s: %s", url, exc)
    return result


# ---------------------------------------------------------------------------
# Search engines
# ---------------------------------------------------------------------------
async def _bing_search(query: str, domain: str = "", limit: int = 8) -> list[dict]:
    q = f"site:{domain} {query}" if domain else query
    url = f"https://www.bing.com/search?q={quote_plus(q)}&setlang=fa-IR"
    try:
        async with _SEARCH_SEM:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(12.0, connect=5.0),
                follow_redirects=True,
                headers={"User-Agent": UA, "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.7"},
            ) as client:
                r = await client.get(url)
        if r.status_code >= 400:
            return []
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
    except Exception as exc:
        _STATS["errors"] += 1
        logger.debug("shopping bing failed: %s", exc)
        return []


async def _ddg_search(query: str, domain: str = "", limit: int = 8) -> list[dict]:
    q = f"site:{domain} {query}" if domain else query
    try:
        async with _SEARCH_SEM:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(12.0, connect=5.0),
                follow_redirects=True,
                headers={"User-Agent": UA, "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.7"},
            ) as client:
                r = await client.get("https://html.duckduckgo.com/html/", params={"q": q})
        if r.status_code >= 400:
            return []
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
    except Exception as exc:
        _STATS["errors"] += 1
        logger.debug("shopping ddg failed: %s", exc)
        return []


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
    try:
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
                        "sort": "price",
                        "source": "torob_search",
                    },
                )
        if r.status_code >= 400:
            return []
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
            price = _parse_price(item.get("price")) or _parse_price(item.get("min_price"))
            key = str(item.get("random_key") or item.get("prk") or "").strip()
            link = str(item.get("page_url") or item.get("url") or "").strip() or (
                f"https://torob.com/p/{key}/" if key else ""
            )
            if (
                not title
                or not price
                or not link
                or link in seen
                or (max_price and price > max_price)
            ):
                continue
            seen.add(link)
            out.append(
                {
                    "title": title,
                    "url": link,
                    "price": price,
                    "seller": str(item.get("seller_name") or "").strip(),
                    "source": "ترب",
                    "availability": str(item.get("availability") or "").strip(),
                }
            )
            if len(out) >= limit:
                break
        if out:
            _STATS["direct_ok"] += 1
        return out
    except Exception as exc:
        _STATS["errors"] += 1
        logger.debug("torob direct failed: %s", exc)
        return []


async def _direct_digikala(query: str, max_price: int, limit: int) -> list[dict]:
    try:
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
                    "https://api.digikala.com/v1/search/",
                    params={"q": query, "page": 1},
                )
        if r.status_code >= 400:
            return []
        data = r.json()
        raw = ((data.get("data") or {}).get("products") if isinstance(data, dict) else None)
        if not isinstance(raw, list):
            return []
        out: list[dict] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title_fa") or item.get("title") or "").strip()
            rial = _parse_price(item.get("selling_price")) or _parse_price(item.get("price"))
            price = (rial // 10) if rial else None
            pid = item.get("id") or item.get("product_id")
            link = str(item.get("url") or "").strip()
            if link.startswith("/"):
                link = "https://www.digikala.com" + link
            if not link and pid:
                link = f"https://www.digikala.com/product/dkp-{pid}/"
            if not title or not price or not link or (max_price and price > max_price):
                continue
            out.append(
                {
                    "title": title,
                    "url": link,
                    "price": price,
                    "seller": "دیجی‌کالا",
                    "source": "دیجی‌کالا",
                    "availability": "",
                }
            )
            if len(out) >= limit:
                break
        if out:
            _STATS["direct_ok"] += 1
        return out
    except Exception as exc:
        _STATS["errors"] += 1
        logger.debug("digikala direct failed: %s", exc)
        return []


async def _direct_site_search(query: str, domain: str, limit: int) -> list[dict]:
    """Best-effort direct catalog/search-page lookup for Iranian stores."""
    template = _SOURCE_SEARCH_URLS.get(domain)
    if not template:
        return []
    url = template.format(q=quote_plus(query))
    try:
        async with _SEARCH_SEM:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(10.0, connect=4.0),
                follow_redirects=True,
                headers={"User-Agent": UA, "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.7"},
            ) as client:
                r = await client.get(url)
        if r.status_code >= 400:
            return []
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
    except Exception as exc:
        logger.debug("direct site search failed %s: %s", domain, exc)
        return []


# ---------------------------------------------------------------------------
# Ranking & diversification
# ---------------------------------------------------------------------------
def _query_variants(query: str, budget: int) -> list[str]:
    q = _clean_query(query)
    variants = [q]
    if budget:
        variants += [f"{q} تا {budget:,} تومان", f"{q} قیمت خرید", f"{q} فروشگاه"]
    else:
        variants += [f"{q} قیمت", f"{q} خرید", f"{q} فروشگاه"]
    out: list[str] = []
    seen: set[str] = set()
    for x in variants:
        x = " ".join(x.split())
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out[:4]


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
    out.sort(key=lambda x: (-float(x.get("_score", 0)), x.get("price") or 10**30))
    return out


def _diversify_shopping_rows(
    rows: list[dict], max_results: int = 10, max_per_source: int = 2
) -> list[dict]:
    """نتایج را بین منابع پخش می‌کند تا یک سایت تمام خروجی را نبلعد."""
    if not rows:
        return []
    result: list[dict] = []
    counts: dict[str, int] = {}
    used_urls: set[str] = set()
    # دور اول: حداقل یک نتیجه از هر منبع معتبر
    for row in rows:
        url = str(row.get("url") or "").strip()
        src = str(row.get("source") or "وب")
        if not url or url in used_urls or counts.get(src, 0) >= 1:
            continue
        used_urls.add(url)
        counts[src] = counts.get(src, 0) + 1
        result.append(row)
        if len(result) >= max_results:
            return result
    # دور دوم: پرکردن ظرفیت باقی‌مانده
    for row in rows:
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
    return (
        "🛒 Shopping Engine v3 (clean)\n"
        + " | ".join(f"{k}={v}" for k, v in _STATS.items())
        + f" | cache={len(_CACHE)}"
    )


# ---------------------------------------------------------------------------
# Optional external guide (mobo.news) – only for ranking, never for price
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
    """موتور خرید نهایی: چندمنبعی واقعی، فیلتر معنایی، تأیید صفحه و بررسی نهایی."""
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

    key = _cache_key(clean, domain or source, max_price, foreign) + ":intent-v4"
    cached = _CACHE.get(key)
    if cached and time.time() - cached[0] < CACHE_TTL:
        _STATS["cache_hits"] += 1
        rows = [dict(x) for x in cached[1]]
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
                    "torob.com",
                    "digikala.com",
                    "technolife.ir",
                    "snappshop.ir",
                    "emalls.ir",
                ]
        else:
            domains = [
                "torob.com",
                "digikala.com",
                "technolife.ir",
                "snappshop.ir",
                "emalls.ir",
                "meghdadit.com",
                "kalaoma.com",
                "19kala.com",
                "mobile.ir",
            ]

        rows: list[dict] = []

        # Direct API sources (highest confidence)
        if not foreign and not domain:
            direct_tasks = []
            for v in variants[:2]:
                direct_tasks += [
                    _direct_torob(v, max_price, max(8, max_results)),
                    _direct_digikala(v, max_price, max(8, max_results)),
                ]
            direct_batches = await asyncio.gather(*direct_tasks, return_exceptions=True)
            for b in direct_batches:
                if isinstance(b, list):
                    for x in b:
                        x["_verified_direct"] = True
                        rows.append(x)

        # Direct site search pages
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

        # Search-engine fallback (never marked as verified)
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
            u = str(x.get("url") or "").strip()
            if not u or u in seen_urls:
                continue
            seen_urls.add(u)
            filtered.append(x)

        rows = _rank(filtered, clean, max_price)

        # Optional mobo.news boost (ranking only)
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

        # Inspect top non-verified pages for real prices
        inspect_candidates = []
        for x in rows:
            if x.get("_verified_direct"):
                continue
            inspect_candidates.append(x)
            if len(inspect_candidates) >= 18:
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
                        old["price"] = obj.price
                        old["seller"] = obj.seller or old.get("seller", "")
                        old["availability"] = obj.availability or old.get(
                            "availability", ""
                        )
                        old["_verified_direct"] = obj.price is not None
                        if obj.source and obj.source != "general":
                            old["source"] = SOURCES.get(
                                obj.source, {"label": obj.source}
                            ).get("label", obj.source)

        # Final filter after inspection
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
            final.append(x)

        final.sort(
            key=lambda x: (-float(x.get("_score", 0)), x.get("price") or 10**30)
        )
        rows = _diversify_shopping_rows(
            final, max_results=max_results, max_per_source=2
        )
        # If only one source really worked, fill remaining slots
        distinct_sources = {str(x.get("source") or "وب") for x in final}
        if len(distinct_sources) <= 1 and len(rows) < min(max_results, len(final)):
            used = {x.get("url") for x in rows}
            for x in final:
                if x.get("url") not in used:
                    rows.append(x)
                    used.add(x.get("url"))
                if len(rows) >= max_results:
                    break

        _CACHE[key] = (time.time(), [dict(x) for x in rows])
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

    lines = [
        f"🛒 **نتایج خرید چندفروشگاهی — {raw}**",
        f"🌍 {market} | 🕒 {now}",
        f"🔎 منابع دارای نتیجه معتبر: {', '.join(source_counts.keys())}",
    ]
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
        "بوده‌اند با نشان تأیید نمایش داده می‌شوند؛ قیمت snippet به‌تنهایی قطعی محسوب نمی‌شود.",
        "",
    ]

    for i, x in enumerate(rows, 1):
        price = x.get("price")
        src = x.get("source") or "وب"
        verified = " ✅" if x.get("_verified_direct") else ""
        lines.append(f"**{i}. {x.get('title') or 'محصول'}**")
        if price and not foreign:
            lines.append(f"🏪 {src}{verified} | 💰 {price:,} تومان")
        elif price:
            lines.append(f"🏪 {src}{verified} | 💰 {price:,}")
        else:
            lines.append(f"🏪 {src} | 💰 قیمت قابل‌تأیید نیست")
        if x.get("seller"):
            lines.append(f"👤 {x['seller']}")
        if x.get("availability"):
            lines.append(f"📦 {x['availability']}")
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

    # Final recommendation
    candidates = [x for x in priced if not max_price or x["price"] <= max_price]
    if candidates:
        for x in candidates:
            src = x.get("source") or "وب"
            x["_final_score"] = (
                float(x.get("_score", 0))
                + TRUST.get(src, 60) * 0.12
                + (8 if x.get("_verified_direct") else 0)
            )
        best = max(candidates, key=lambda x: x["_final_score"])
        model_key = _shopping_model_key(best.get("title"))
        same_model = [
            x
            for x in candidates
            if _shopping_model_key(x.get("title")) == model_key and model_key
        ]
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
