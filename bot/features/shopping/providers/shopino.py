"""Shopino (شاپینو) shopping provider — shopino.app

استراتژی:
1) API عمومی شاپینو (اگر در دسترس باشد)
2) HTML صفحه جستجو
3) جستجوی وب با site:shopino.app (DuckDuckGo / Bing) — وقتی دامنه از سرور ربات
   timeout می‌دهد، معمولاً همین مسیر جواب می‌دهد
"""
from __future__ import annotations

import re
from urllib.parse import quote_plus, urlparse

import httpx
from bs4 import BeautifulSoup

from bot.features.shopping.shared import (
    UA,
    _SEARCH_SEM,
    _STATS,
    _circuit_is_open,
    _with_retry,
    _normalize_market_price,
    _is_used_listing,
    _wants_used,
)

SEARCH_URL = "https://shopino.app/search?q={q}"
API_CANDIDATES = [
    "https://api-go.shopino.app/v1/products/search",
    "https://api-go.shopino.app/products/search",
    "https://api.shopino.app/v1/search",
]


def _parse_price_fa(text: str) -> int | None:
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", text.replace("٬", "").replace(",", ""))
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def _product_link(href: str) -> str:
    href = (href or "").strip()
    if not href:
        return ""
    if href.startswith("/"):
        href = "https://shopino.app" + href
    if "shopino.app" not in href:
        return ""
    return href.split("?")[0].rstrip("/")


async def _shopino_api(query: str, max_price: int, limit: int) -> list[dict]:
    out: list[dict] = []
    params = {"q": query, "query": query, "search": query, "page": 1, "limit": max(limit, 12)}
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(6.0, connect=2.5),
        follow_redirects=True,
        headers={
            "User-Agent": UA,
            "Accept": "application/json",
            "Accept-Language": "fa-IR,fa;q=0.9",
            "Origin": "https://shopino.app",
            "Referer": "https://shopino.app/",
        },
    ) as client:
        for url in API_CANDIDATES:
            try:
                r = await client.get(url, params=params)
                if r.status_code >= 400:
                    continue
                data = r.json()
            except Exception:
                continue
            items = None
            if isinstance(data, dict):
                for key in ("results", "products", "items", "data"):
                    if isinstance(data.get(key), list):
                        items = data[key]
                        break
                    if isinstance(data.get(key), dict) and isinstance(
                        data[key].get("items"), list
                    ):
                        items = data[key]["items"]
                        break
            elif isinstance(data, list):
                items = data
            if not items:
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                title = str(
                    item.get("title") or item.get("name") or item.get("product_name") or ""
                ).strip()
                price_raw = (
                    item.get("price")
                    or item.get("final_price")
                    or item.get("sale_price")
                    or item.get("min_price")
                )
                price = _normalize_market_price(price_raw, title) or _parse_price_fa(
                    str(price_raw or "")
                )
                pid = str(item.get("id") or item.get("product_id") or "").strip()
                link = str(
                    item.get("url") or item.get("permalink") or item.get("link") or ""
                ).strip()
                if not link and pid:
                    link = f"https://shopino.app/product/{pid}"
                link = _product_link(link) or link
                if not title or not price or not link:
                    continue
                if max_price and price > max_price:
                    continue
                if _is_used_listing(title) and not _wants_used(query):
                    continue
                seller = str(
                    item.get("shop_name")
                    or item.get("seller")
                    or item.get("store_name")
                    or ""
                ).strip()
                out.append(
                    {
                        "title": title,
                        "url": link,
                        "price": price,
                        "seller": seller,
                        "source": "شاپینو",
                        "availability": "موجود",
                    }
                )
                if len(out) >= limit:
                    return out
            if out:
                return out
    return out


async def _shopino_html(query: str, max_price: int, limit: int) -> list[dict]:
    url = SEARCH_URL.format(q=quote_plus(query))
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(8.0, connect=3.0),
        follow_redirects=True,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "fa-IR,fa;q=0.9",
        },
    ) as client:
        r = await client.get(url)
    if r.status_code >= 400:
        raise RuntimeError(f"shopino html {r.status_code}")
    soup = BeautifulSoup(r.text, "html.parser")
    out: list[dict] = []
    seen: set[str] = set()
    for a in soup.select("a[href*='/product/']"):
        href = _product_link(a.get("href") or "")
        if not href or href in seen:
            continue
        title = " ".join(a.stripped_strings)[:120].strip()
        parent = a.parent
        block_txt = parent.get_text(" ", strip=True) if parent else a.get_text(" ", strip=True)
        price = None
        for m in re.finditer(r"([\d٬,]{3,})\s*تومان", block_txt):
            price = _parse_price_fa(m.group(1))
            if price and price >= 10_000:
                break
        if not title or not price:
            continue
        if max_price and price > max_price:
            continue
        if _is_used_listing(title) and not _wants_used(query):
            continue
        seen.add(href)
        out.append(
            {
                "title": title,
                "url": href,
                "price": price,
                "seller": "",
                "source": "شاپینو",
                "availability": "موجود",
            }
        )
        if len(out) >= limit:
            break
    return out


async def _shopino_web_site_search(query: str, max_price: int, limit: int) -> list[dict]:
    """جستجوی وب محدود به shopino.app — وقتی خود سایت timeout می‌دهد."""
    q = f"site:shopino.app {query} تومان"
    out: list[dict] = []
    seen: set[str] = set()

    async def _ddg() -> list[dict]:
        rows: list[dict] = []
        url = "https://html.duckduckgo.com/html/"
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=4.0),
            follow_redirects=True,
            headers={"User-Agent": UA, "Accept-Language": "fa-IR,fa;q=0.9"},
        ) as client:
            r = await client.post(url, data={"q": q})
        if r.status_code >= 400:
            return rows
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select("a.result__a, a.result-link, a[href]"):
            href = (a.get("href") or "").strip()
            # DDG redirect
            if "uddg=" in href:
                m = re.search(r"uddg=([^&]+)", href)
                if m:
                    from urllib.parse import unquote

                    href = unquote(m.group(1))
            if "shopino.app" not in href or "/product/" not in href:
                continue
            href = _product_link(href) or href
            if not href or href in seen:
                continue
            title = a.get_text(" ", strip=True)[:120]
            if not title or len(title) < 4:
                continue
            # قیمت از snippet
            parent = a.find_parent("div") or a.parent
            snip = parent.get_text(" ", strip=True) if parent else title
            price = None
            for m in re.finditer(r"([\d٬,]{3,})\s*(?:تومان|تومن)", snip):
                price = _parse_price_fa(m.group(1))
                if price and price >= 10_000:
                    break
            if max_price and price and price > max_price:
                continue
            # اگر قیمت در اسنیپت نبود، لینک را نگه می‌داریم با price=0 فیلتر نشود؟
            # برای اعتماد، فقط با قیمت قبول کن
            if not price:
                continue
            seen.add(href)
            rows.append(
                {
                    "title": title,
                    "url": href,
                    "price": price,
                    "seller": "",
                    "source": "شاپینو",
                    "availability": "موجود",
                }
            )
            if len(rows) >= limit:
                break
        return rows

    async def _bing() -> list[dict]:
        rows: list[dict] = []
        url = f"https://www.bing.com/search?q={quote_plus(q)}&setlang=fa"
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=4.0),
            follow_redirects=True,
            headers={"User-Agent": UA, "Accept-Language": "fa-IR,fa;q=0.9"},
        ) as client:
            r = await client.get(url)
        if r.status_code >= 400:
            return rows
        soup = BeautifulSoup(r.text, "html.parser")
        for li in soup.select("li.b_algo, .b_algo"):
            a = li.select_one("h2 a, a")
            if not a:
                continue
            href = (a.get("href") or "").strip()
            if "shopino.app" not in href or "/product/" not in href:
                continue
            href = _product_link(href) or href
            if not href or href in seen:
                continue
            title = a.get_text(" ", strip=True)[:120]
            snip_el = li.select_one(".b_caption p, p")
            snip = snip_el.get_text(" ", strip=True) if snip_el else li.get_text(" ", strip=True)
            price = None
            for m in re.finditer(r"([\d٬,]{3,})\s*(?:تومان|تومن)", snip):
                price = _parse_price_fa(m.group(1))
                if price and price >= 10_000:
                    break
            if not title or not price:
                continue
            if max_price and price > max_price:
                continue
            seen.add(href)
            rows.append(
                {
                    "title": title,
                    "url": href,
                    "price": price,
                    "seller": "",
                    "source": "شاپینو",
                    "availability": "موجود",
                }
            )
            if len(rows) >= limit:
                break
        return rows

    try:
        out = await _ddg()
    except Exception:
        out = []
    if len(out) < limit:
        try:
            more = await _bing()
            for r in more:
                if r["url"] not in seen:
                    out.append(r)
                    seen.add(r["url"])
                if len(out) >= limit:
                    break
        except Exception:
            pass
    return out[:limit]


async def _direct_shopino(query: str, max_price: int, limit: int) -> list[dict]:
    if _circuit_is_open("shopino"):
        # حتی با circuit، web site search را یک‌بار امتحان کن
        try:
            async with _SEARCH_SEM:
                rows = await _shopino_web_site_search(query, max_price, limit)
            return rows or []
        except Exception:
            return []

    async def _do() -> list[dict]:
        async with _SEARCH_SEM:
            rows = await _shopino_api(query, max_price, limit)
            if not rows:
                try:
                    rows = await _shopino_html(query, max_price, limit)
                except Exception:
                    rows = []
            if not rows:
                rows = await _shopino_web_site_search(query, max_price, limit)
            if rows:
                _STATS["direct_ok"] += 1
            return rows

    result = await _with_retry(_do, source="shopino", max_attempts=2)
    return result if isinstance(result, list) else []
