"""Shopino (شاپینو) shopping provider — shopino.app"""
from __future__ import annotations

import re
from urllib.parse import quote_plus

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


async def _shopino_api(query: str, max_price: int, limit: int) -> list[dict]:
    out: list[dict] = []
    params = {"q": query, "query": query, "search": query, "page": 1, "limit": max(limit, 12)}
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(8.0, connect=3.5),
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
                    if isinstance(data.get(key), dict) and isinstance(data[key].get("items"), list):
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
                price = _normalize_market_price(price_raw, title) or _parse_price_fa(str(price_raw or ""))
                pid = str(item.get("id") or item.get("product_id") or "").strip()
                link = str(item.get("url") or item.get("permalink") or item.get("link") or "").strip()
                if not link and pid:
                    link = f"https://shopino.app/product/{pid}"
                if not title or not price or not link:
                    continue
                if max_price and price > max_price:
                    continue
                if _is_used_listing(title) and not _wants_used(query):
                    continue
                seller = str(
                    item.get("shop_name") or item.get("seller") or item.get("store_name") or ""
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
        timeout=httpx.Timeout(10.0, connect=4.0),
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
    cards = soup.select("a[href*='/product/'], [class*='product'], [data-product-id], article")
    for card in cards:
        a = card if card.name == "a" else card.select_one("a[href*='/product/']")
        if not a:
            continue
        href = (a.get("href") or "").strip()
        if "/product/" not in href:
            continue
        if href.startswith("/"):
            href = "https://shopino.app" + href
        if href in seen:
            continue
        title = " ".join(a.stripped_strings)[:120].strip()
        if not title:
            title_el = card.select_one("h2, h3, [class*='title'], [class*='name']")
            title = title_el.get_text(" ", strip=True)[:120] if title_el else ""
        price_el = card.select_one("[class*='price'], [class*='Price'], [data-price]")
        price_txt = price_el.get_text(" ", strip=True) if price_el else card.get_text(" ", strip=True)
        price = None
        for m in re.finditer(r"([\d٬,]{3,})\s*تومان", price_txt):
            price = _parse_price_fa(m.group(1))
            if price:
                break
        if not price:
            price = _normalize_market_price(_parse_price_fa(price_txt), title)
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


async def _direct_shopino(query: str, max_price: int, limit: int) -> list[dict]:
    if _circuit_is_open("shopino"):
        return []

    async def _do() -> list[dict]:
        async with _SEARCH_SEM:
            rows = await _shopino_api(query, max_price, limit)
            if not rows:
                rows = await _shopino_html(query, max_price, limit)
            if rows:
                _STATS["direct_ok"] += 1
            return rows

    result = await _with_retry(_do, source="shopino")
    return result if isinstance(result, list) else []
