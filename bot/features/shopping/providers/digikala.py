"""Digikala shopping provider."""
from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from bot.features.shopping.shared import (
    UA,
    _SEARCH_SEM,
    _STATS,
    _circuit_is_open,
    _with_retry,
    _parse_price,
    _normalize_market_price,
    _normalize_availability,
    _is_used_listing,
    _wants_used,
    _jsonld_products,
    logger,
)

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



async def _direct_digikala(query: str, max_price: int, limit: int) -> list[dict]:
    if _circuit_is_open("digikala"):
        return []

    async def _do() -> list[dict]:
        async with _SEARCH_SEM:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(6.5, connect=3.0),
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

    # retry کمتر و سریع‌تر — الگوی userscript (timeout کوتاه + یک بار تلاش اضافه)
    result = await _with_retry(_do, source="digikala", max_attempts=2, base_delay=0.25)
    rows = result if isinstance(result, list) else []
    if not rows:
        rows = await _digikala_html_fallback(query, max_price, limit)
    return rows



