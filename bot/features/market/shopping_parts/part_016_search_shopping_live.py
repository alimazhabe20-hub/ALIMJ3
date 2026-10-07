"""Authoritative live shopping search for Rooze Ziba.

Rules:
- Iran is the default market.
- Foreign/global sites are searched only when explicitly requested.
- No AI is required for shopping.
- Never invent a product, price, stock status, seller, or link.
- Budget filters are extracted from the user's original Persian/Arabic text.
- Direct catalog endpoints are attempted first where available; search engines
  are used as a broad fallback.
"""
from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from urllib.parse import quote_plus, urlparse

import httpx
from bs4 import BeautifulSoup

try:
    from bot.logger import logger
except Exception:  # pragma: no cover
    import logging
    logger = logging.getLogger("rooze_ziba")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128 Safari/537.36 RoozeZiba/4.0"
)

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
}

FOREIGN_ALIASES = {
    "amazon": "amazon.com", "آمازون": "amazon.com",
    "ebay": "ebay.com", "ایبی": "ebay.com",
    "aliexpress": "aliexpress.com", "علی اکسپرس": "aliexpress.com",
    "علی‌اکسپرس": "aliexpress.com",
    "walmart": "walmart.com", "وال مارت": "walmart.com",
    "bestbuy": "bestbuy.com", "best buy": "bestbuy.com",
    "etsy": "etsy.com", "اتسی": "etsy.com",
    "newegg": "newegg.com",
    "noon": "noon.com", "نون": "noon.com",
    "temu": "temu.com", "تیمو": "temu.com",
    "shein": "shein.com", "شین": "shein.com",
}

IRAN_ALIASES = {
    "دیجی کالا": "digikala.com", "دیجی‌کالا": "digikala.com", "digikala": "digikala.com",
    "ترب": "torob.com", "torob": "torob.com",
    "تکنولایف": "technolife.ir", "technolife": "technolife.ir",
    "اسنپ شاپ": "snappshop.ir", "اسنپ‌شاپ": "snappshop.ir", "snappshop": "snappshop.ir",
    "ایمالز": "emalls.ir", "emalls": "emalls.ir",
    "موبایل دات آی آر": "mobile.ir", "mobile.ir": "mobile.ir",
    "باسلام": "basalam.com", "basalam": "basalam.com",
}

DIGIT_TRANS = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
    "01234567890123456789",
)


def _digits(text: str) -> str:
    return str(text or "").translate(DIGIT_TRANS)


def _clean_number_text(text: str) -> str:
    return _digits(text).replace(",", "").replace("٬", "").replace(" ", "")


def _budget(text: str) -> int:
    """Extract a Persian budget in toman; never convert an arbitrary number."""
    t = _digits(text).replace(",", "").replace("٬", "")
    patterns = (
        # «تا 50 میلیون»، «زیر 50 م»، «بودجه 50 میلیون»
        r"(?:بودجه|تا|زیر|حداکثر|حدود|حد)\s*(\d+(?:\.\d+)?)\s*(میلیون|م)\b",
        # «50 میلیون تومان»
        r"(\d+(?:\.\d+)?)\s*(میلیون|م)\s*(?:تومان|تومن)?",
        # «تا 50000000 تومان»
        r"(?:بودجه|تا|زیر|حداکثر|حدود|حد)\s*([0-9]{5,})\s*(?:تومان|تومن)?",
    )
    for pattern in patterns:
        m = re.search(pattern, t, re.I)
        if not m:
            continue
        try:
            value = float(m.group(1))
            unit = m.group(2) if len(m.groups()) > 1 else ""
            if unit in ("میلیون", "م"):
                value *= 1_000_000
            if value >= 100_000:
                return int(value)
        except Exception:
            continue
    return 0


def _is_phone(text: str) -> bool:
    return bool(re.search(
        r"گوشی|موبایل|اسمارت\s*فون|smart\s*phone|iphone|آیفون|سامسونگ|"
        r"شیائومی|پوکو|honor|oneplus|pixel|پیکسل",
        str(text or ""), re.I,
    ))


def _explicit_domain(text: str) -> str:
    q = str(text or "").lower()
    aliases = {**IRAN_ALIASES, **FOREIGN_ALIASES}
    for alias, domain in sorted(aliases.items(), key=lambda x: -len(x[0])):
        if alias.lower() in q:
            return domain
    m = re.search(
        r"(?:https?://)?(?:www\.)?([a-z0-9][a-z0-9.-]+\.[a-z]{2,})(?:/[^\s]*)?",
        q,
    )
    return m.group(1).lower().rstrip(".") if m else ""


def _foreign_requested(text: str) -> bool:
    q = str(text or "").lower()
    markers = (
        "سایت خارجی", "سایت‌های خارجی", "سایت های خارجی",
        "منابع خارجی", "بازار جهانی", "بازار بین‌المللی", "بازار بین المللی",
        "خارجی هم", "بین‌المللی", "بین المللی", "جهانی",
    )
    if any(x in q for x in markers):
        return True
    return any(alias.lower() in q for alias in FOREIGN_ALIASES)


def _strip_site_words(text: str) -> str:
    q = str(text or "").strip()
    for alias in sorted({**IRAN_ALIASES, **FOREIGN_ALIASES}, key=len, reverse=True):
        q = re.sub(rf"\b{re.escape(alias)}\b", " ", q, flags=re.I)
    q = re.sub(r"(?:https?://)?(?:www\.)?[a-z0-9][a-z0-9.-]+\.[a-z]{2,}(?:/[^\s]*)?", " ", q, flags=re.I)
    q = re.sub(r"\s+", " ", q)
    return q.strip(" ؟?!،,") or str(text or "").strip()


def _parse_price(value) -> int | None:
    if value is None:
        return None
    s = _digits(str(value)).replace(",", "").replace("٬", "")
    m = re.search(r"\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        n = float(m.group(0))
        return int(n) if n > 0 else None
    except Exception:
        return None


def _price_from_text(text: str) -> int | None:
    if not text:
        return None
    text = str(text)
    patterns = (
        r"([0-9۰-۹]{1,3}(?:[,٬][0-9۰-۹]{3}){1,4})\s*(?:تومان|تومن|ت)\b",
        r"([0-9۰-۹]{5,})\s*(?:تومان|تومن|ت)\b",
        r"(?:قیمت|price|قیمت فروش|قیمت نهایی)\s*[:：]?\s*([0-9۰-۹]{5,})",
    )
    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            price = _parse_price(m.group(1))
            if price:
                return price
    return None


def _host(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        return ""


def _source(url: str) -> str:
    return IRAN_SITES.get(_host(url), _host(url) or "وب")


def _title_ok(title: str, query: str) -> bool:
    if not title:
        return False
    if _is_phone(query):
        return bool(re.search(
            r"گوشی|موبایل|iphone|آیفون|samsung|سامسونگ|xiaomi|شیائومی|"
            r"poco|پوکو|pixel|پیکسل|honor",
            title, re.I,
        ))
    return True


async def _search_engine(
    engine: str,
    query: str,
    *,
    domain: str = "",
    limit: int = 8,
) -> list[dict]:
    q = query.strip()
    if domain:
        q = f"site:{domain} {q}"

    if engine == "bing":
        url = f"https://www.bing.com/search?q={quote_plus(q)}&setlang=fa-IR"
        selector = "li.b_algo"
    else:
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(q)}"
        selector = ".result"

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(14.0, connect=5.0),
            follow_redirects=True,
            headers={
                "User-Agent": UA,
                "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.7",
            },
        ) as client:
            response = await client.get(url)
            if response.status_code >= 400:
                logger.warning("shopping %s HTTP %s query=%s", engine, response.status_code, q)
                return []
            html = response.text

        soup = BeautifulSoup(html, "html.parser")
        out = []
        if engine == "bing":
            items = soup.select(selector)[:limit]
            for item in items:
                a = item.select_one("h2 a")
                cap = item.select_one(".b_caption p")
                if not a:
                    continue
                href = (a.get("href") or "").strip()
                title = a.get_text(" ", strip=True)
                snippet = cap.get_text(" ", strip=True) if cap else ""
                if href.startswith("http") and title:
                    out.append({"url": href, "title": title, "snippet": snippet})
        else:
            items = soup.select(selector)[:limit]
            for item in items:
                a = item.select_one(".result__a")
                cap = item.select_one(".result__snippet")
                if not a:
                    continue
                href = (a.get("href") or "").strip()
                title = a.get_text(" ", strip=True)
                snippet = cap.get_text(" ", strip=True) if cap else ""
                if href.startswith("http") and title:
                    out.append({"url": href, "title": title, "snippet": snippet})

        logger.info("shopping search engine=%s query=%s results=%s", engine, q, len(out))
        return out
    except Exception as exc:
        logger.warning("shopping %s failed: %s", engine, exc)
        return []


async def _direct_torob(query: str, max_price: int, limit: int) -> list[dict]:
    url = "https://api.torob.com/v4/base-product/search/"
    params = {
        "q": query,
        "page": 0,
        "size": min(max(12, limit * 2), 40),
        "sort": "price",
        "source": "torob_search",
    }
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(12.0, connect=5.0),
            follow_redirects=True,
            headers={"User-Agent": UA, "Accept": "application/json", "Accept-Language": "fa-IR,fa;q=0.9"},
        ) as client:
            r = await client.get(url, params=params)
            if r.status_code >= 400:
                logger.warning("shopping torob HTTP %s", r.status_code)
                return []
            data = r.json()
    except Exception as exc:
        logger.warning("shopping torob failed: %s", exc)
        return []

    raw = data.get("results") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        return []

    out, seen = [], set()
    for item in raw:
        if not isinstance(item, dict) or item.get("is_adv") is True:
            continue
        title = str(item.get("name1") or item.get("name") or item.get("title") or "").strip()
        price = _parse_price(item.get("price")) or _parse_price(item.get("min_price"))
        if not title or not price or (max_price and price > max_price):
            continue
        key = str(item.get("random_key") or item.get("prk") or "").strip()
        link = str(item.get("page_url") or item.get("url") or "").strip()
        if not link and key:
            link = f"https://torob.com/p/{key}/"
        if not link or link in seen:
            continue
        seen.add(link)
        out.append({
            "title": title,
            "url": link,
            "price": price,
            "seller": str(item.get("seller_name") or "").strip(),
            "source": "ترب",
            "availability": str(item.get("availability") or "").strip(),
        })
        if len(out) >= limit:
            break
    return out


async def _direct_digikala(query: str, max_price: int, limit: int) -> list[dict]:
    url = "https://api.digikala.com/v1/search/"
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(12.0, connect=5.0),
            follow_redirects=True,
            headers={"User-Agent": UA, "Accept": "application/json", "Accept-Language": "fa-IR,fa;q=0.9"},
        ) as client:
            r = await client.get(url, params={"q": query, "page": 1})
            if r.status_code >= 400:
                logger.warning("shopping digikala HTTP %s", r.status_code)
                return []
            data = r.json()
    except Exception as exc:
        logger.warning("shopping digikala failed: %s", exc)
        return []

    raw = ((data.get("data") or {}).get("products") if isinstance(data, dict) else None)
    if not isinstance(raw, list):
        return []

    out = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title_fa") or item.get("title") or "").strip()
        # Digikala commonly exposes prices in Rial; convert to Toman once.
        rial = _parse_price(item.get("selling_price")) or _parse_price(item.get("price"))
        price = (rial // 10) if rial else None
        if not title or not price or (max_price and price > max_price):
            continue
        pid = item.get("id") or item.get("product_id")
        link = str(item.get("url") or "").strip()
        if link.startswith("/"):
            link = "https://www.digikala.com" + link
        if not link and pid:
            link = f"https://www.digikala.com/product/dkp-{pid}/"
        if not link:
            continue
        out.append({
            "title": title,
            "url": link,
            "price": price,
            "seller": "دیجی‌کالا",
            "source": "دیجی‌کالا",
            "availability": "",
        })
        if len(out) >= limit:
            break
    return out


def _dedupe(results: list[dict], query: str, max_price: int) -> list[dict]:
    seen = set()
    unique = []
    qwords = set(re.findall(r"[\w\u0600-\u06ff]+", query.lower()))

    for item in results:
        url = str(item.get("url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)

        price = item.get("price")
        if price is not None:
            try:
                price = int(price)
            except Exception:
                price = None
        if max_price and price is not None and price > max_price:
            continue

        title = str(item.get("title") or "").strip()
        words = set(re.findall(r"[\w\u0600-\u06ff]+", title.lower()))
        relevance = len(qwords & words)
        item["price"] = price
        item["_score"] = (1 if price is not None else 0, relevance)
        unique.append(item)

    unique.sort(key=lambda x: (-x["_score"][0], -x["_score"][1], x.get("price") or 10**30))
    return unique


def _format_result(
    query: str,
    results: list[dict],
    *,
    foreign: bool,
    budget: int,
) -> str:
    market = "بازار جهانی" if foreign else "بازار ایران"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if not results:
        if budget:
            return (
                f"🔎 جستجوی زنده برای «{query}» انجام شد.\n"
                f"💳 سقف بودجه: {budget:,} تومان\n\n"
                "⚠️ در منابع زنده‌ای که بررسی شد، نتیجه‌ای با قیمت قابل‌تأیید پیدا نشد.\n"
                "من قیمت یا مدل را حدس نمی‌زنم."
            )
        return (
            f"🔎 جستجوی زنده برای «{query}» انجام شد.\n\n"
            "⚠️ نتیجه قابل‌تأییدی از منابع زنده پیدا نشد؛ قیمت حدسی ارائه نمی‌کنم."
        )

    lines = [
        f"🛒 **نتیجه جستجوی زنده — {market}**",
        f"🕒 زمان جستجو: {now}",
        "ℹ️ قیمت‌ها فقط از داده زنده استخراج شده‌اند؛ قیمت حدسی نمایش داده نمی‌شود.",
        "",
    ]

    for i, item in enumerate(results, 1):
        title = item.get("title") or "محصول"
        price = item.get("price")
        lines.append(f"{i}. **{title}**")
        lines.append(
            f"🏪 {item.get('source') or 'وب'}"
            + (f" | 💰 {int(price):,} تومان" if price is not None else " | 💰 قیمت در نتیجه مشخص نشد")
        )
        if item.get("seller"):
            lines.append(f"👤 فروشنده: {item['seller']}")
        if item.get("availability"):
            lines.append(f"📦 وضعیت: {item['availability']}")
        lines.append(f"🔗 {item['url']}")
        lines.append("")

    priced = [x for x in results if x.get("price") is not None]
    if priced:
        cheapest = min(priced, key=lambda x: int(x["price"]))
        lines.append(
            f"🏆 ارزان‌ترین نتیجه قابل‌تأیید: **{int(cheapest['price']):,} تومان**"
        )
    if budget:
        lines.append(f"💳 سقف بودجه اعمال‌شده: **{budget:,} تومان**")
    lines.append("⚠️ قبل از خرید، قیمت و موجودی همان صفحه را دوباره بررسی کن.")
    return "\n".join(lines)


async def search_shopping(
    query: str = "",
    source: str = "all",
    max_results: int = 10,
    min_price: int = 0,
    max_price: int = 0,
    user_id: int = 0,
) -> str:
    """Run a real-time, non-AI shopping search."""
    query = " ".join(str(query or "").split()).strip()
    if not query:
        return "عبارت محصول برای جستجو مشخص نیست."

    try:
        max_results = max(4, min(int(max_results or 10), 12))
    except Exception:
        max_results = 10

    explicit = _explicit_domain(query)
    foreign = _foreign_requested(query)

    # Naming an Iranian store is explicit but does not turn the market global.
    if explicit in IRAN_SITES:
        foreign = False
    elif explicit and explicit not in IRAN_SITES:
        foreign = True

    budget = _budget(query)
    if budget and not max_price:
        max_price = budget
    try:
        min_price = max(0, int(min_price or 0))
        max_price = max(0, int(max_price or 0))
    except Exception:
        min_price, max_price = 0, budget

    clean = _strip_site_words(query)
    if budget and _is_phone(query):
        clean = f"گوشی موبایل تا {budget:,} تومان"

    results: list[dict] = []

    # Common high-value Iranian phone request: use live catalog endpoints
    # concurrently, then broaden to several Iranian web sources.
    if _is_phone(query) and not foreign and not explicit:
        direct = await asyncio.gather(
            _direct_torob("گوشی موبایل", max_price or 0, max_results),
            _direct_digikala("گوشی موبایل", max_price or 0, max_results),
            return_exceptions=True,
        )
        for batch in direct:
            if isinstance(batch, list):
                results.extend(batch)

    # Search engine layer. It is always live and broad; foreign is opt-in.
    if not results:
        if explicit:
            domains = [explicit]
        elif foreign:
            domains = ["amazon.com", "ebay.com", "walmart.com", "bestbuy.com", "aliexpress.com"]
        else:
            # Iran only by default. Broad Iranian web + key Iranian marketplaces.
            domains = [
                "torob.com", "digikala.com", "technolife.ir",
                "mobile.ir", "emalls.ir", "snappshop.ir", "basalam.com",
            ]

        queries = [clean]
        if budget and _is_phone(query):
            queries.extend([
                f"گوشی موبایل تا {budget:,} تومان",
                f"گوشی سامسونگ تا {budget:,} تومان",
                f"گوشی شیائومی تا {budget:,} تومان",
                f"گوشی پوکو تا {budget:,} تومان",
            ])

        tasks = []
        # Keep fan-out bounded: two engines across a small number of sources.
        for domain in domains[:7]:
            for q in queries[:2]:
                tasks.append(_search_engine("bing", q, domain=domain, limit=max(4, max_results // 2)))
                tasks.append(_search_engine("ddg", q, domain=domain, limit=max(4, max_results // 2)))

        # For explicit foreign request, add one broad-web query without site lock.
        if foreign and not explicit:
            tasks.append(_search_engine("bing", clean, limit=max_results))
            tasks.append(_search_engine("ddg", clean, limit=max_results))

        batches = await asyncio.gather(*tasks, return_exceptions=True)
        for batch in batches:
            if not isinstance(batch, list):
                continue
            for item in batch:
                title = str(item.get("title") or "")
                if not _title_ok(title, query):
                    continue
                item["price"] = _price_from_text(
                    f"{title} {item.get('snippet') or ''}"
                )
                item["source"] = _source(item.get("url", "")) if not foreign else (
                    _host(item.get("url", "")) or "وب"
                )
                if max_price and item.get("price") is not None and item["price"] > max_price:
                    continue
                if min_price and item.get("price") is not None and item["price"] < min_price:
                    continue
                # In the Iran-default mode do not leak foreign domains from a
                # generic web result.
                if not foreign and _host(item.get("url", "")) not in IRAN_SITES:
                    continue
                results.append(item)

    unique = _dedupe(results, clean, max_price)
    # If a budget is present, never fill the list with over-budget items.
    if max_price:
        unique = [
            x for x in unique
            if x.get("price") is None or int(x["price"]) <= max_price
        ]
    unique = unique[:max_results]

    return _format_result(query, unique, foreign=foreign, budget=budget)
