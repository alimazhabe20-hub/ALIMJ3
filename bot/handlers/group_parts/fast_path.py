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
    # تحلیل بازار
    if re.search(r"تحلیل\s*طلا|طلا\s*را?\s*تحلیل", t, re.I):
        return "analyze_gold"
    if re.search(r"تحلیل\s*(?:بیتکوین|بیت‌کوین|اتریوم|btc|eth)|(?:بیتکوین|btc)\s*را?\s*تحلیل", t, re.I):
        return "analyze_crypto"
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
            from bot.handlers.group_parts.group_ui import price_card
            msg = price_card("قیمت دلار", _fmt_toman(price) + " تومان", source="TGJU · به‌روز")
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




        if intent == "analyze_gold":
            try:
                from bot.features.market.finance import analyze_gold
                import asyncio
                if asyncio.iscoroutinefunction(analyze_gold):
                    report = await asyncio.wait_for(analyze_gold("1h"), timeout=10.0)
                else:
                    report = await asyncio.wait_for(asyncio.to_thread(analyze_gold, "1h"), timeout=10.0)
                if report:
                    return f"🥇 <b>تحلیل طلا</b>\n━━━━━━━━━━━━━━\n{str(report)[:3500]}"
            except Exception as exc:
                logger.warning("analyze_gold fast_path: %s", exc)
            return None

        if intent == "analyze_crypto":
            try:
                import asyncio, re as _re
                sym = "btc"
                if _re.search(r"اتریوم|eth", text, _re.I):
                    sym = "eth"
                from bot.features.market.finance import analyze_crypto
                if asyncio.iscoroutinefunction(analyze_crypto):
                    report = await asyncio.wait_for(analyze_crypto(sym), timeout=12.0)
                else:
                    report = await asyncio.wait_for(asyncio.to_thread(analyze_crypto, sym), timeout=12.0)
                if report:
                    return f"🪙 <b>تحلیل {sym.upper()}</b>\n━━━━━━━━━━━━━━\n{str(report)[:3500]}"
            except Exception as exc:
                logger.warning("analyze_crypto fast_path: %s", exc)
            return None

        if intent == "weather":
            import asyncio
            city = _extract_city(text)
            try:
                from bot.api.api_weather import get_weather
                if asyncio.iscoroutinefunction(get_weather):
                    w = await asyncio.wait_for(get_weather(city), timeout=12.0)
                else:
                    w = await asyncio.wait_for(asyncio.to_thread(get_weather, city), timeout=12.0)
                msg = _format_weather(city, w)
                if msg and "در دسترس نیست" not in msg:
                    _cache_set(f"weather:{city}", msg)
                    return msg
                # اگر dict خالی/None بود
                if not msg:
                    return f"⚠️ آب‌وهوای «{city}» الان در دسترس نیست. کمی بعد دوباره امتحان کن."
                return msg
            except Exception as exc:
                logger.warning("weather fast_path failed city=%s: %s", city, exc)
                return f"⚠️ دریافت آب‌وهوای «{city}» ممکن نشد. کمی بعد دوباره امتحان کن."

        if intent == "shop":

            import asyncio
            from urllib.parse import quote
            # کوئری تمیز برای جستجو — شبیه پیام اصلی ربات
            q_clean = re.sub(r"^(?:ربات|هوشمند|!)\s*", "", text or "", flags=re.I).strip()
            q_clean = re.sub(
                r"\b(?:برام|برای\s*من|لینکش?\s*بفرست|پیدا\s*کن|جستجو\s*کن)\b",
                " ",
                q_clean,
            )
            q_clean = " ".join(q_clean.split()) or (text or "").strip()
            try:
                from bot.features.market import shopping as _sh
                if hasattr(_sh, "_CIRCUIT"):
                    # مدارهای مرده را باز کن تا دوباره شانس داشته باشند
                    _sh._CIRCUIT.clear()
            except Exception:
                pass
            result = None
            try:
                from bot.features.market.shopping import search_shopping
                # API-first سریع؛ timeout کمی بالاتر از قبل برای نتیجه واقعی
                result = await asyncio.wait_for(
                    search_shopping(q_clean, source="all", max_results=6),
                    timeout=14.0,
                )
            except Exception as exc:
                logger.warning("shop fast_path search failed: %s", exc)
                result = None
            # فقط وقتی نتیجه واقعی و مفید بود جواب بده
            if result and len(str(result)) > 40 and "کامل نبود" not in str(result):
                bad = (
                    ("پیدا نشد" in str(result))
                    or ("مشخص نیست" in str(result))
                    or ("قابل‌اعتماد" in str(result) and "پیدا نشد" in str(result))
                    or ("نتیجهٔ زنده و قابل‌اعتماد پیدا نشد" in str(result))
                )
                if not bad:
                    body = str(result)[:3500]
                    # خروجی موتور خرید Markdown است؛ برای گروه به HTML نزدیک کن
                    body = (
                        body.replace("**", "")
                        .replace("🛒 نتایج خرید چندفروشگاهی", "🛒 نتایج خرید")
                    )
                    try:
                        from bot.handlers.group_parts.group_ui import shop_card
                        return shop_card(body)
                    except Exception:
                        return "🛒 <b>نتایج خرید</b>\n━━━━━━━━━━━━━━\n" + body
            # شکست کنترل‌شده: لینک تمیز HTML (مثل ربات اصلی) نه URL خام encoded
            try:
                from bot.handlers.group_parts.group_ui import shop_fallback
                return shop_fallback(q_clean)
            except Exception:
                q = quote((q_clean or "")[:80])
                return (
                    "🛒 <b>جستجوی خرید</b>\n━━━━━━━━━━━━━━\n"
                    f"برای «{q_clean[:50]}» نتیجه زنده پیدا نشد؛ قیمت حدسی ارائه نمی‌کنم.\n\n"
                    f"🔎 <a href=\"https://torob.com/search/?query={q}\">ترب</a>"
                    f"  ·  "
                    f"🛍 <a href=\"https://www.digikala.com/search/?q={q}\">دیجی‌کالا</a>"
                )


    except Exception as exc:
        logger.warning("fast_path %s failed: %s", intent, exc)
        return None
    return None
