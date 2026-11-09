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
    # خرید فقط با درخواست واضح — نه فقط نام کالا
    if re.search(r"(?:پیدا\s*کن|برام\s*بخر|میخوام\s*بخرم|لینک\s*بده)", t, re.I):
        return "shop"
    if re.search(r"(?:باتری|باطری|شارژر|گوشی)", t, re.I) and re.search(r"(?:پیدا|بخر|قیمت|چند|میخوام)", t, re.I):
        return "shop"
    return None


def _extract_city(text: str) -> str:
    # الگوی ساده: هوای X / آب و هوای X
    m = re.search(r"(?:هوای|آب[‌ ]?و[‌ ]?هوای|دمای)\s+([^\s?؟]+)", text)
    if m:
        return m.group(1).strip()
    # پیش‌فرض
    return "تهران"



def _format_weather(city: str, w) -> str:
    """تبدیل خروجی get_weather (dict یا str) به متن خوانا."""
    if w is None:
        return ""
    if isinstance(w, str):
        s = w.strip()
        if s.startswith("{") and "temp" in s:
            # احتمالاً str(dict)
            try:
                import ast
                w = ast.literal_eval(s)
            except Exception:
                return s
        else:
            return s
    if not isinstance(w, dict):
        return str(w)

    def g(*keys, default="—"):
        for k in keys:
            if k in w and w[k] is not None and str(w[k]).strip() != "":
                return w[k]
        return default

    temp = g("temp", "temperature", "temperature_2m")
    feels = g("feels_like", "apparent_temperature", default=None)
    cond = g("condition", "desc", "description", "weather")
    humidity = g("humidity", "relative_humidity_2m")
    wind = g("wind", "wind_speed", "wind_speed_10m")
    pressure = g("pressure", "surface_pressure")
    high = g("high", "temp_max", default=None)
    low = g("low", "temp_min", default=None)
    source = g("source", default="")

    lines = [f"🌤️ <b>آب‌وهوا · {city}</b>", "━━━━━━━━━━━━━━"]
    lines.append(f"🌡️ دما: <b>{temp}</b>°C")
    if feels is not None:
        lines.append(f"🤚 حس واقعی: {feels}°C")
    lines.append(f"☁️ وضعیت: {cond}")
    lines.append(f"💧 رطوبت: {humidity}%")
    lines.append(f"💨 باد: {wind} m/s")
    if pressure not in ("—", None):
        lines.append(f"🔵 فشار: {pressure} hPa")
    if high is not None or low is not None:
        lines.append(f"⬆️⬇️ بیشینه/کمینه: {high if high is not None else '—'} / {low if low is not None else '—'}°C")
    if source:
        lines.append(f"<i>منبع: {source}</i>")
    return "\n".join(lines)


async def run_fast_path(text: str) -> Optional[str]:
    """اجرای fast-path؛ در صورت موفقیت متن آماده برمی‌گرداند."""
    intent = detect_fast_intent(text)
    logger.info("fast_path intent=%s text=%r", intent, (text or "")[:60])
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



        if intent == "shop":
            import asyncio
            from urllib.parse import quote
            # کوئری تمیز برای جستجو
            q_clean = re.sub(r"^(?:ربات|هوشمند)\s*", "", text or "", flags=re.I).strip()
            q_clean = re.sub(r"\b(?:برام|برای من|لینکش?\s*بفرست|پیدا\s*کن)\b", " ", q_clean)
            q_clean = " ".join(q_clean.split())
            try:
                from bot.features.market import shopping as _sh
                if hasattr(_sh, "_CIRCUIT"):
                    # فقط مدارهای مرده را کمی باز کن
                    _sh._CIRCUIT.clear()
            except Exception:
                pass
            result = None
            try:
                from bot.features.market.shopping import search_shopping
                result = await asyncio.wait_for(
                    search_shopping(q_clean or text, source="torob", max_results=5),
                    timeout=12.0,
                )
            except Exception as exc:
                logger.warning("shop fast_path search failed: %s", exc)
                result = None
            # اگر نتیجه واقعی و مفید بود
            if result and len(str(result)) > 40 and "کامل نبود" not in str(result):
                bad = ("پیدا نشد" in str(result)) or ("مشخص نیست" in str(result))
                if not bad:
                    return f"🛒 <b>نتایج خرید</b>\n━━━━━━━━━━━━━━\n{result}"
            # شکست: None برگردان تا AI مسیر قبلی (بهتر) فعال شود
            return None
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
            msg = _format_weather(city, w)
            if not msg:
                return None
            _cache_set(cache_key, msg)
            return msg

    except Exception as exc:
        logger.warning("fast_path %s failed: %s", intent, exc)
        return None
    return None
