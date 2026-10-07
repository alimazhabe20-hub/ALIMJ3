"""Live shopping search for Rooze Ziba.

Design goals:
- Iran is the default market.
- Foreign sites are searched only when the user explicitly names/asks for them.
- No AI dependency: shopping must still work when Gemini/Groq/etc. fail.
- Prices are shown only when extracted from a live source/result.
- Keep network fan-out bounded so the Telegram event loop is not flooded.
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
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128 Safari/537.36 RoozeZiba/4.0"
)

_IRAN_SITES = {
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

_FOREIGN_ALIASES = {
    "amazon": "amazon.com", "آمازون": "amazon.com",
    "ebay": "ebay.com", "ایبی": "ebay.com",
    "aliexpress": "aliexpress.com", "علی اکسپرس": "aliexpress.com", "علی‌اکسپرس": "aliexpress.com",
    "walmart": "walmart.com", "وال مارت": "walmart.com",
    "bestbuy": "bestbuy.com", "best buy": "bestbuy.com",
    "etsy": "etsy.com", "اتسی": "etsy.com",
    "newegg": "newegg.com",
    "noon": "noon.com", "نون": "noon.com",
    "temu": "temu.com", "تیمو": "temu.com",
    "shein": "shein.com", "شین": "shein.com",
}

_IRAN_EXPLICIT_ALIASES = {
    "دیجی کالا": "digikala.com", "دیجی‌کالا": "digikala.com", "digikala": "digikala.com",
    "ترب": "torob.com", "torob": "torob.com",
    "تکنولایف": "technolife.ir", "technolife": "technolife.ir",
    "اسنپ شاپ": "snappshop.ir", "اسنپ‌شاپ": "snappshop.ir", "snappshop": "snappshop.ir",
    "ایمالز": "emalls.ir", "emalls": "emalls.ir",
    "موبایل دات آی آر": "mobile.ir", "mobile.ir": "mobile.ir",
    "باسلام": "basalam.com", "basalam": "basalam.com",
}


def _digits(text: str) -> str:
    return str(text or "").translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))


def _budget(text: str) -> int:
    t = _digits(text).replace(",", "").replace("٬", "")
    patterns = (
        r"(?:بودجه|تا|زیر|حداکثر|حدود|حد)\s*(\d+(?:\.\d+)?)\s*(?:میلیون|م)\b",
        r"(\d+(?:\.\d+)?)\s*(?:میلیون|م)\s*(?:تومان|تومن)?",
        r"(?:بودجه|تا|زیر|حداکثر|حدود|حد)\s*(\d{5,})\s*(?:تومان|تومن)?",
    )
    for pattern in patterns:
        m = re.search(pattern, t, re.I)
        if not m:
            continue
        try:
            n = float(m.group(1))
            if "میلیون" in m.group(0) or re.search(r"\d+(?:\.\d+)?\s*م\b", m.group(0)):
                n *= 1_000_000
            if n >= 100_000:
                return int(n)
        except Exception:
            pass
    return 0


def _is_phone(text: str) -> bool:
    return bool(re.search(
        r"گوشی|موبایل|اسمارت\s*فون|smart\s*phone|iphone|آیفون|سامسونگ|شیائومی|پوکو|honor|oneplus|pixel",
        str(text or ""), re.I,
    ))


def _explicit_domain(text: str) -> str:
    q = str(text or "").lower()
    for alias, domain in sorted({**_IRAN_EXPLICIT_ALIASES, **_FOREIGN_ALIASES}.items(), key=lambda x: -len(x[0])):
        if alias in q:
            return domain
    m = re.search(r"(?:https?://)?(?:www\.)?([a-z0-9][a-z0-9.-]+\.[a-z]{2,})(?:/[^\s]*)?", q)
    return m.group(1).lower().rstrip(".") if m else ""


def _is_foreign_explicit(text: str) -> bool:
    q = str(text or "").lower()
    markers = (
        "سایت خارجی", "سایت‌های خارجی", "سایت های خارجی", "بازار جهانی", "خارجی",
        "amazon", "آمازون", "ebay", "ایبی", "aliexpress", "علی اکسپرس", "علی‌اکسپرس",
        "walmart", "best buy", "bestbuy", "etsy", "newegg", "noon", "temu", "shein",
    )
    return any(x in q for x in markers)


def _strip_site_words(text: str) -> str:
    q = str(text or "").strip()
    q = re.sub(r"(?:برو|برو تو|برو داخل|وارد شو به|داخل|در|توی|تو)\s+(?:سایت\s+)?[\w\u0600-\u06ff .-]+", "", q, count=1, flags=re.I)
    q = re.sub(r"(?:https?://)?(?:www\.)?[a-z0-9][a-z0-9.-]+\.[a-z]{2,}(?:/[^\s]*)?", "", q, flags=re.I)
    return " ".join(q.split()).strip(" ؟?!،,") or str(text or "").strip()


def _parse_price(value) -> int | None:
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
    if not text:
        return None
    patterns = (
        r"([0-9۰-۹]{1,3}(?:[,٬][0-9۰-۹]{3}){1,4})\s*(?:تومان|تومن|ت)\b",
        r"([0-9۰-۹]{5,})\s*(?:تومان|تومن|ت)\b",
        r"(?:قیمت|price|قیمت فروش|قیمت نهایی)\s*[:：]?\s*([0-9۰-۹]{5,})",
    )
    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            p = _parse_price(m.group(1))
            if p:
                return p
    return None


def _title_ok(title: str, query: str) -> bool:
    if not title:
        return False
    if _is_phone(query):
        return bool(re.search(r"گوشی|موبایل|iphone|آیفون|samsung|سامسونگ|xiaomi|شیائومی|poco|پوکو|pixel|honor", title, re.I))
    return True


async def _bing_search(query: str, *, domain: str = "", limit: int = 8) -> list[dict]:
    q = query.strip()
    if domain:
        q = f"site:{domain} {q}"
    url = f"https://www.bing.com/search?q={quote_plus(q)}&setlang=fa-IR"
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=4.0),
            follow_redirects=True,
            headers={"User-Agent": UA, "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.7"},
        ) as client:
            r = await client.get(url)
            if r.status_code >= 400:
                return []
        soup = BeautifulSoup(r.text, "html.parser")
        out = []
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
        logger.info("shopping search engine=bing query=%s results=%s", q, len(out))
        return out
    except Exception as exc:
        logger.warning("shopping bing failed: %s", exc)
        return []


async def _ddg_search(query: str, *, domain: str = "", limit: int = 8) -> list[dict]:
    """DuckDuckGo HTML fallback; useful when Bing returns sparse Persian shopping results."""
    q = query.strip()
    if domain:
        q = f"site:{domain} {q}"
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(q)}"
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(12.0, connect=5.0),
            follow_redirects=True,
            headers={"User-Agent": UA, "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.7"},
        ) as client:
            r = await client.get(url)
            if r.status_code >= 400:
                return []
        soup = BeautifulSoup(r.text, "html.parser")
        out = []
        for item in soup.select(".result")[:limit]:
            a = item.select_one("a.result__a")
            if not a:
                continue
            href = (a.get("href") or "").strip()
            title = a.get_text(" ", strip=True)
            sn = item.select_one(".result__snippet")
            snippet = sn.get_text(" ", strip=True) if sn else ""
            if href.startswith("http") and title:
                out.append({"url": href, "title": title, "snippet": snippet})
        logger.info("shopping search engine=ddg query=%s results=%s", q, len(out))
        return out
    except Exception as exc:
        logger.warning("shopping ddg failed: %s", exc)
        return []


async def _direct_torob(query: str, max_price: int, limit: int) -> list[dict]:
    url = "https://api.torob.com/v4/base-product/search/"
    params = {"q": query, "page": 0, "size": min(max(10, limit * 2), 30), "sort": "price", "source": "torob_search"}
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(9.0, connect=4.0),
            follow_redirects=True,
            headers={"User-Agent": UA, "Accept": "application/json", "Accept-Language": "fa-IR,fa;q=0.9"},
        ) as client:
            r = await client.get(url, params=params)
            if r.status_code >= 400:
                logger.warning("torob live HTTP %s", r.status_code)
                return []
            data = r.json()
    except Exception as exc:
        logger.warning("torob live failed: %s", exc)
        return []
    raw = data.get("results") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        return []
    out = []
    seen = set()
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
        out.append({"title": title, "url": link, "price": price, "seller": str(item.get("seller_name") or "").strip(), "source": "ترب", "availability": str(item.get("availability") or "").strip()})
        if len(out) >= limit:
            break
    return out


async def _direct_digikala(query: str, max_price: int, limit: int) -> list[dict]:
    url = "https://api.digikala.com/v1/search/"
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(9.0, connect=4.0),
            follow_redirects=True,
            headers={"User-Agent": UA, "Accept": "application/json", "Accept-Language": "fa-IR,fa;q=0.9"},
        ) as client:
            r = await client.get(url, params={"q": query, "page": 1})
            if r.status_code >= 400:
                logger.warning("digikala live HTTP %s", r.status_code)
                return []
            data = r.json()
    except Exception as exc:
        logger.warning("digikala live failed: %s", exc)
        return []
    raw = ((data.get("data") or {}).get("products") if isinstance(data, dict) else None)
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title_fa") or item.get("title") or "").strip()
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
        out.append({"title": title, "url": link, "price": price, "seller": "دیجی‌کالا", "source": "دیجی‌کالا", "availability": ""})
        if len(out) >= limit:
            break
    return out


async def _direct_generic_sources(query: str, max_price: int, limit: int) -> list[dict]:
    """Fast direct catalog search for ordinary Iranian products, not just phones."""
    clean = " ".join(str(query or "").split()).strip()
    if not clean:
        return []
    variants = [clean, f"{clean} قیمت", f"{clean} خرید"]
    seen = set()
    out = []
    for v in variants:
        batches = await asyncio.gather(
            _direct_torob(v, max_price, limit),
            _direct_digikala(v, max_price, limit),
            return_exceptions=True,
        )
        for batch in batches:
            if not isinstance(batch, list):
                continue
            for item in batch:
                url = str(item.get("url") or "")
                if url and url not in seen:
                    seen.add(url)
                    out.append(item)
                    if len(out) >= limit * 2:
                        return out
    return out


def _generic_relevance(title: str, query: str) -> int:
    """Score meaningful product/category tokens; ignore filler words."""
    stop = {
        "یه", "یک", "برای", "برام", "من", "میخوام", "می‌خوام", "پیدا", "کن", "بکن",
        "میشه", "لطفا", "لطفاً", "بهم", "مناسب", "خرید", "قیمت", "قیمتش", "فروش",
        "تو", "تا", "زیر", "بودجه", "مردانه", "زنانه", "بچه", "بچگانه",
    }
    qwords = [w for w in re.findall(r"[\w\u0600-\u06ff]+", _digits(query).lower()) if w not in stop and len(w) > 1]
    t = _digits(title).lower()
    return sum(1 for w in qwords if w in t)


async def search_shopping(
    query: str = "",
    source: str = "all",
    max_results: int = 10,
    min_price: int = 0,
    max_price: int = 0,
    user_id: int = 0,
) -> str:
    query = " ".join(str(query or "").split()).strip()
    if not query:
        return "عبارت محصول برای جستجو مشخص نیست."
    max_results = max(4, min(int(max_results or 10), 12))
    domain = _explicit_domain(query)
    foreign = _is_foreign_explicit(query)
    budget = _budget(query)
    if budget and not max_price:
        max_price = budget

    # Default market = Iran. Foreign is opt-in only.
    if foreign and not domain:
        # User explicitly asked for global/foreign search; broad web search is allowed.
        domain = ""
    if domain and not foreign and domain not in _IRAN_SITES and domain not in _IRAN_EXPLICIT_ALIASES.values():
        foreign = True

    clean_query = _strip_site_words(query)
    clean_query = re.sub(r"(?:یه|یک|لطفاً|لطفا|برام|بهم|برای من|میخوام|می‌خوام|پیدا کن|پیدا کن برام|برام پیدا کن)", " ", clean_query, flags=re.I)
    clean_query = " ".join(clean_query.split()).strip() or query
    if budget and _is_phone(query):
        clean_query = f"گوشی موبایل تا {budget:,} تومان"

    results: list[dict] = []

    # Fast live Iranian catalog path for the common phone+budget request.
    if budget and _is_phone(query) and not foreign and not domain:
        direct_tasks = [
            _direct_torob("گوشی موبایل", budget, max_results),
            _direct_digikala("گوشی موبایل", budget, max_results),
        ]
        direct_batches = await asyncio.gather(*direct_tasks, return_exceptions=True)
        for batch in direct_batches:
            if isinstance(batch, list):
                results.extend(batch)
        # If APIs return nothing, fall back to live Bing results instead of a dead end.
        if not results:
            batches = await asyncio.gather(
                _bing_search(clean_query, domain="torob.com", limit=max_results),
                _bing_search(clean_query, domain="digikala.com", limit=max_results),
                _bing_search(clean_query, domain="technolife.ir", limit=max_results),
                _bing_search(clean_query, domain="mobile.ir", limit=max_results),
                _bing_search(clean_query, domain="", limit=max_results),
                return_exceptions=True,
            )
            for batch in batches:
                if isinstance(batch, list):
                    for x in batch:
                        price = _price_from_text((x.get("title") or "") + " " + (x.get("snippet") or ""))
                        if max_price and price and price > max_price:
                            continue
                        if _title_ok(x.get("title", ""), query):
                            x["price"] = price
                            x["source"] = _IRAN_SITES.get(urlparse(x["url"]).netloc.lower().replace("www.", ""), "وب")
                            results.append(x)

    else:
        if domain:
            batches = await asyncio.gather(
                *[_bing_search(clean_query + " قیمت خرید", domain=domain, limit=max_results) for _ in range(2)],
                return_exceptions=True,
            )
        elif foreign:
            batches = await asyncio.gather(
                _bing_search(clean_query + " price buy", domain="", limit=max_results),
                _bing_search(clean_query + " product price", domain="", limit=max_results),
                return_exceptions=True,
            )
        else:
            # Iran default: first hit real Iranian catalogs directly, then use web search.
            direct = await _direct_generic_sources(clean_query, max_price, max_results)
            results.extend(direct)
            search_terms = [
                clean_query + " قیمت خرید",
                clean_query + " تومان فروشگاه",
            ]
            batches = await asyncio.gather(
                *[
                    _bing_search(term, domain=dom, limit=max_results)
                    for term in search_terms
                    for dom in ("torob.com", "digikala.com", "emalls.ir", "technolife.ir")
                ],
                *[
                    _ddg_search(term, domain=dom, limit=max_results)
                    for term in search_terms[:1]
                    for dom in ("torob.com", "digikala.com", "emalls.ir", "technolife.ir")
                ],
                return_exceptions=True,
            )
        for batch in batches:
            if isinstance(batch, list):
                for x in batch:
                    text = (x.get("title") or "") + " " + (x.get("snippet") or "")
                    x["price"] = _price_from_text(text)
                    host = urlparse(x.get("url", "")).netloc.lower().replace("www.", "")
                    x["source"] = _IRAN_SITES.get(host, host or "وب")
                    if max_price and x.get("price") and x["price"] > max_price:
                        continue
                    results.append(x)

    # Deduplicate and score: priced results first, then title relevance.
    seen = set()
    unique = []
    qwords = set(re.findall(r"[\w\u0600-\u06ff]+", clean_query.lower()))
    for x in results:
        url = x.get("url", "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        title = str(x.get("title") or "")
        words = set(re.findall(r"[\w\u0600-\u06ff]+", title.lower()))
        relevance = len(qwords & words)
        # For ordinary product requests, don't return arbitrary products merely
        # because a store search happened to return them. At least one meaningful
        # product token must appear in the title.
        if not _is_phone(query) and not foreign and _generic_relevance(title, clean_query) <= 0:
            continue
        x["_score"] = (1 if x.get("price") else 0, relevance, _generic_relevance(title, clean_query))
        unique.append(x)
    unique.sort(key=lambda x: (-x["_score"][0], -x["_score"][2], -x["_score"][1], x.get("price") or 10**30))
    unique = unique[:max_results]

    if not unique:
        return f"برای «{query}» در منابع زنده نتیجه قابل‌تأییدی پیدا نشد؛ قیمت حدسی ارائه نمی‌کنم."

    searched_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    market_label = "بازار جهانی" if foreign else "بازار ایران"
    lines = [
        f"🛒 **نتیجه جستجوی زنده — {market_label}**",
        f"🕒 زمان جستجو: {searched_at}",
        "قیمت فقط در صورت استخراج از نتیجه زنده نمایش داده شده؛ قیمت حدسی نداریم.",
        "",
    ]
    for i, x in enumerate(unique, 1):
        title = x.get("title") or "محصول"
        price = x.get("price")
        price_text = f"{price:,} تومان" if price else "قیمت در نتیجه مشخص نشد"
        lines.append(f"{i}. **{title}**")
        lines.append(f"🏪 {x.get('source') or 'وب'} | 💰 {price_text}")
        if x.get("seller"):
            lines.append(f"👤 فروشنده: {x['seller']}")
        if x.get("availability"):
            lines.append(f"📦 وضعیت: {x['availability']}")
        lines.append(f"🔗 {x['url']}")
        lines.append("")
    priced = [x for x in unique if x.get("price")]
    if priced:
        cheapest = min(priced, key=lambda x: x["price"])
        lines.append(f"🏆 ارزان‌ترین نتیجه با قیمت قابل‌تأیید: **{cheapest['price']:,} تومان**")
    if budget:
        lines.append(f"💳 سقف بودجه اعمال‌شده: **{budget:,} تومان**")
    return "\n".join(lines)
