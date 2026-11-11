"""Torob shopping provider."""
from __future__ import annotations

import httpx

from bot.features.shopping.shared import (
    UA,
    _SEARCH_SEM,
    _STATS,
    _circuit_is_open,
    _with_retry,
    _normalize_market_price,
    _normalize_availability,
    _is_used_listing,
    _wants_used,
)

async def _direct_torob(query: str, max_price: int, limit: int) -> list[dict]:
    if _circuit_is_open("torob"):
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
                r = await client.get(
                    "https://api.torob.com/v4/base-product/search/",
                    params={
                        "q": query,
                        "page": 0,
                        "size": min(max(12, limit * 2), 40),
                        # برای بودجه بالا sort=price فقط مدل‌های خیلی ارزان می‌آورد
                        **({"sort": "price"} if (max_price and max_price < 8_000_000) else {}),
                        "source": "next",
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




