"""
Fast-path گروهی: جواب سریع بدون LLM برای موضوعات مشخص.
قیمت ارز/طلا/کریپتو، آب‌وهوا، اوقات شرعی ساده.
"""
from __future__ import annotations

import re
import time
from typing import Optional, Tuple

from bot.logger import logger

# کش ساده حافظه‌ای
_CACHE: dict[str, tuple[float, str]] = {}
_TTL = 45.0  # ثانیه


def _cache_get(key: str) -> Optional[str]:
    item = _CACHE.get(key)
    if not item:
        return None
    ts, val = item
    if time.time() - ts > _TTL:
        return None
    return val


def _cache_set(key: str, val: str) -> None:
    _CACHE[key] = (time.time(), val)


def _fmt_toman(rial_or_toman: int, *, already_toman: bool = False) -> str:
    v = int(rial_or_toman)
    # tgju معمولاً ریال می‌دهد؛ نمایش تومان
    if not already_toman and v > 100_000:
        v = v // 10
    return f"{v:,}"


_CRYPTO_MAP = {
    "بیتکوین": "btc",
    "بیت‌کوین": "btc",
    "بیت کوین": "btc",
    "btc": "btc",
    "bitcoin": "btc",
    "اتریوم": "eth",
    "eth": "eth",
    "ethereum": "eth",
    "تتر": "usdt",
    "usdt": "usdt",
    "sol": "sol",
    "سولانا": "sol",
}


def detect_fast_intent(text: str) -> Optional[str]:
    """برگرداندن نوع fast-path یا None."""
    if not text:
        return None
    t = text.strip()
    low = t.lower()

    # دلار / یورو
    if re.search(r"قیمت\s*دلار|دلار\s*چند|نرخ\s*دلار|dollar", t, re.I):
        return "dollar"
    if re.search(r"قیمت\s*یورو|یورو\s*چند|نرخ\s*یورو", t, re.I):
        return "euro"
    # طلا
    if re.search(r"قیمت\s*طلا|طلای\s*۱۸|گرم\s*۱۸|طلا\s*چند", t, re.I):
        return "gold"
    # کریپتو ساده
    for fa, sym in _CRYPTO_MAP.items():
        if fa in low or fa in t:
            if re.search(r"قیمت|چند|چقدر|نرخ", t, re.I) or len(t) <= 24:
                return f"crypto:{sym}"
    # هوا
    if re.search(r"هوا|آب\s*و\s*هوا|دما|باران", t, re.I):
        return "weather"
    return None


def _extract_city(text: str) -> str:
    # الگوی ساده: هوای X / آب و هوای X
    m = re.search(r"(?:هوای|آب[‌ ]?و[‌ ]?هوای|دمای)\s+([^\s?؟]+)", text)
    if m:
        return m.group(1).strip()
    # پیش‌فرض
    return "تهران"


async def run_fast_path(text: str) -> Optional[str]:
    """اجرای fast-path؛ در صورت موفقیت متن آماده برمی‌گرداند."""
    intent = detect_fast_intent(text)
    if not intent:
        return None

    cached = _cache_get(intent if not intent.startswith("crypto:") else intent)
    if cached and intent != "weather":
        return cached

    try:
        if intent == "dollar":
            from bot.api.tgju import get_dollar_price
            price = await get_dollar_price()
            if not price:
                return None
            msg = (
                f"💵 <b>قیمت دلار</b>\n"
                f"━━━━━━━━━━━━━━\n"
                f"نرخ: <b>{_fmt_toman(price)}</b> تومان\n"
                f"<i>منبع: TGJU · به‌روز</i>"
            )
            _cache_set("dollar", msg)
            return msg

        if intent == "euro":
            from bot.api.tgju import get_market_prices
            data = await get_market_prices()
            # fallback: try bulk key
            price = None
            if isinstance(data, dict):
                price = data.get("euro") or data.get("price_eur")
            if not price:
                try:
                    from bot.api.tgju import _fetch_bulk, _parse_price
                    bulk = await _fetch_bulk()
                    item = bulk.get("price_eur") or bulk.get("price_euro") or {}
                    price = _parse_price(item.get("p") if isinstance(item, dict) else item)
                except Exception:
                    price = None
            if not price:
                return None
            msg = (
                f"💶 <b>قیمت یورو</b>\n"
                f"━━━━━━━━━━━━━━\n"
                f"نرخ: <b>{_fmt_toman(int(price))}</b> تومان\n"
                f"<i>منبع: TGJU · به‌روز</i>"
            )
            _cache_set("euro", msg)
            return msg

        if intent == "gold":
            from bot.api.tgju import get_gold18_price
            price = await get_gold18_price()
            if not price:
                return None
            msg = (
                f"🥇 <b>طلای ۱۸ عیار</b>\n"
                f"━━━━━━━━━━━━━━\n"
                f"هر گرم: <b>{_fmt_toman(price)}</b> تومان\n"
                f"<i>منبع: TGJU · به‌روز</i>"
            )
            _cache_set("gold", msg)
            return msg

        if intent.startswith("crypto:"):
            sym = intent.split(":", 1)[1]
            from bot.features.market.finance import get_crypto_price
            result = await get_crypto_price(sym)
            if not result or "خطا" in str(result) or "یافت" in str(result):
                return None
            # result ممکن است متن آماده باشد
            msg = f"🪙 <b>{sym.upper()}</b>\n━━━━━━━━━━━━━━\n{result}"
            _cache_set(intent, msg)
            return msg

        if intent == "weather":
            city = _extract_city(text)
            cache_key = f"weather:{city}"
            cached_w = _cache_get(cache_key)
            if cached_w:
                return cached_w
            from bot.features.weather import get_weather
            # get_weather ممکن است sync باشد
            import asyncio
            if asyncio.iscoroutinefunction(get_weather):
                w = await get_weather(city)
            else:
                w = await asyncio.to_thread(get_weather, city)
            if not w:
                return None
            msg = f"🌤️ <b>آب‌وهوا · {city}</b>\n━━━━━━━━━━━━━━\n{w}"
            _cache_set(cache_key, msg)
            return msg

    except Exception as exc:
        logger.warning("fast_path %s failed: %s", intent, exc)
        return None
    return None
