"""Crypto opportunity scanner: top-500 universe -> selected-TF scan -> deep top-5.

Designed as a new market module so the stable/legacy market cores do not need
large edits. It reuses the project's existing Binance/OKX data path and TA/ICT
engines, with bounded concurrency and short-lived caching.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction

from bot.logger import logger
from bot.utils.http_client import pooled_async_client, request_with_retry, safe_json
from bot.features.market.finance import _fetch_klines_interval, _pair_from_symbol
from bot.features.market.finance_ta import (
    _compute_ta,
    _score_timeframe,
    _atr,
    _detect_candle_patterns,
    _price_action_analysis,
    _advanced_levels,
)
from bot.features.market.finance_ict import analyze_ict_from_ohlc


TIMEFRAMES = {
    "15m": ("۱۵ دقیقه", "15m"),
    "1h": ("۱ ساعت", "1h"),
    "4h": ("۴ ساعت", "4h"),
    "1d": ("روزانه", "1d"),
}

_CACHE: dict[str, tuple[float, Any]] = {}
_CACHE_TTL = 120.0
_SEMAPHORE = asyncio.Semaphore(14)

# Assets that normally do not provide a useful long/short technical setup.
_STABLES = {
    "USDT", "USDC", "BUSD", "DAI", "FDUSD", "TUSD", "USDE", "USDD",
    "PYUSD", "USDP", "FRAX", "EURC", "USD1", "RLUSD", "GUSD",
}


def opportunity_timeframe_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🕒 ۱۵ دقیقه", callback_data="buy:scan:15m"),
            InlineKeyboardButton("⏰ ۱ ساعت", callback_data="buy:scan:1h"),
        ],
        [
            InlineKeyboardButton("🕓 ۴ ساعت", callback_data="buy:scan:4h"),
            InlineKeyboardButton("📅 روزانه", callback_data="buy:scan:1d"),
        ],
        [InlineKeyboardButton("🔙 بازگشت به بازار", callback_data="buy:back")],
    ])


def _cache_get(key: str):
    item = _CACHE.get(key)
    if not item:
        return None
    if time.monotonic() - item[0] > _CACHE_TTL:
        _CACHE.pop(key, None)
        return None
    return item[1]


def _cache_put(key: str, value: Any):
    _CACHE[key] = (time.monotonic(), value)
    # Keep this feature cache bounded.
    if len(_CACHE) > 16:
        oldest = sorted(_CACHE.items(), key=lambda x: x[1][0])[:6]
        for k, _ in oldest:
            _CACHE.pop(k, None)


async def _keep_typing(bot, chat_id, stop_event: asyncio.Event):
    """Keep Telegram 'typing…' status alive while the long scan runs."""
    while not stop_event.is_set():
        try:
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        except Exception as exc:
            logger.debug("opportunity typing action failed: %s", exc)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=4.0)
        except asyncio.TimeoutError:
            pass
        except Exception as exc:
            logger.debug("opportunity typing wait failed: %s", exc)


async def _top_500() -> list[dict[str, Any]]:
    cached = _cache_get("top500")
    if cached is not None:
        return cached

    coins: list[dict[str, Any]] = []
    try:
        async with pooled_async_client() as client:
            for page in (1, 2):
                r = await request_with_retry(
                    "GET",
                    "https://api.coingecko.com/api/v3/coins/markets",
                    params={
                        "vs_currency": "usd",
                        "order": "market_cap_desc",
                        "per_page": 250,
                        "page": page,
                        "sparkline": "false",
                        "price_change_percentage": "24h,7d",
                    },
                )
                if r.status_code != 200:
                    logger.warning("opportunity top500 page %s status=%s", page, r.status_code)
                    break
                batch = safe_json(r) or []
                if not batch:
                    break
                coins.extend(batch)
    except Exception as exc:
        logger.warning("opportunity top500 failed: %s", exc)

    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rank, coin in enumerate(coins[:500], 1):
        sym = str(coin.get("symbol") or "").upper().strip()
        cid = str(coin.get("id") or "").strip()
        if not sym or not cid or sym in _STABLES or sym in seen:
            continue
        # Binance pair construction is intentionally conservative; symbols that
        # are not listed will simply fail the bounded OHLCV request and be skipped.
        seen.add(sym)
        result.append({
            "rank": rank,
            "id": cid,
            "symbol": sym,
            "name": str(coin.get("name") or sym),
            "market_cap": float(coin.get("market_cap") or 0),
            "volume": float(coin.get("total_volume") or 0),
            "price": float(coin.get("current_price") or 0),
            "chg24": float(coin.get("price_change_percentage_24h") or 0),
            "chg7": float(coin.get("price_change_percentage_7d_in_currency") or 0),
        })

    _cache_put("top500", result)
    return result


def _ohlcv_parts(rows: list) -> tuple[list, list, list, list, list]:
    opens: list[float] = []
    highs: list[float] = []
    lows: list[float] = []
    closes: list[float] = []
    vols: list[float] = []
    for row in rows or []:
        try:
            opens.append(float(row[1])); highs.append(float(row[2]))
            lows.append(float(row[3])); closes.append(float(row[4]))
            vols.append(float(row[5]))
        except Exception:
            continue
    return opens, highs, lows, closes, vols


def _direction_label(direction: str, score: float) -> str:
    if direction == "صعودی" and score >= 6:
        return "لانگ 🟢"
    if direction == "نزولی" and score >= 6:
        return "شورت 🔴"
    return "خنثی 🟡"


def _extra_indicators(closes: list[float], highs: list[float], lows: list[float]) -> dict[str, float | None]:
    """Lightweight indicators not exposed by the existing TA core."""
    def sma(values, n):
        return sum(values[-n:]) / n if len(values) >= n else None

    def ema(values, n):
        if len(values) < n:
            return None
        value = sum(values[:n]) / n
        alpha = 2 / (n + 1)
        for x in values[n:]:
            value = alpha * x + (1 - alpha) * value
        return value

    e12, e26 = ema(closes, 12), ema(closes, 26)
    macd = (e12 - e26) if e12 is not None and e26 is not None else None
    signal = None
    if len(closes) >= 35:
        macd_series = []
        # Rebuild a compact MACD series for the last window.
        for i in range(26, len(closes) + 1):
            e12_i = ema(closes[:i], 12)
            e26_i = ema(closes[:i], 26)
            if e12_i is not None and e26_i is not None:
                macd_series.append(e12_i - e26_i)
        signal = ema(macd_series, 9) if len(macd_series) >= 9 else None

    mid = sma(closes, 20)
    std = None
    if len(closes) >= 20 and mid is not None:
        w = closes[-20:]
        std = (sum((x - mid) ** 2 for x in w) / 20) ** 0.5
    upper = mid + 2 * std if mid is not None and std is not None else None
    lower = mid - 2 * std if mid is not None and std is not None else None

    stoch = None
    if len(closes) >= 14:
        hh, ll = max(highs[-14:]), min(lows[-14:])
        stoch = ((closes[-1] - ll) / (hh - ll) * 100) if hh > ll else 50.0

    return {
        "ema12": e12, "ema26": e26, "macd": macd, "macd_signal": signal,
        "bb_mid": mid, "bb_upper": upper, "bb_lower": lower, "stoch": stoch,
    }


def _fast_candidate(coin: dict[str, Any], rows: list) -> dict[str, Any] | None:
    o, h, l, c, v = _ohlcv_parts(rows)
    if len(c) < 60:
        return None
    ta = _compute_ta(c, h, l, v)
    ta["atr"] = _atr(h, l, c, 14)
    ta["patterns"] = _detect_candle_patterns(o, h, l, c)
    ta.update(_extra_indicators(c, h, l))
    score, direction, adx = _score_timeframe(ta)
    if direction not in ("صعودی", "نزولی") or score < 6:
        return None
    vol_ratio = float(ta.get("vol_ratio") or 1)
    # Small volume confirmation bonus, capped to keep the score interpretable.
    rank_score = float(score) * 10.0
    if adx >= 25:
        rank_score += 4
    if 0.8 <= float(ta.get("rsi") or 50) <= 70:
        rank_score += 2
    if vol_ratio >= 1.25:
        rank_score += 3
    if vol_ratio < 0.6:
        rank_score -= 3
    macd, macd_signal = ta.get("macd"), ta.get("macd_signal")
    if macd is not None and macd_signal is not None:
        if direction == "صعودی" and macd > macd_signal:
            rank_score += 3
        elif direction == "نزولی" and macd < macd_signal:
            rank_score += 3
    bb_u, bb_l = ta.get("bb_upper"), ta.get("bb_lower")
    if bb_u is not None and bb_l is not None and bb_u > bb_l:
        if direction == "صعودی" and c[-1] > ta.get("bb_mid", c[-1]):
            rank_score += 2
        elif direction == "نزولی" and c[-1] < ta.get("bb_mid", c[-1]):
            rank_score += 2
    return {
        "coin": coin,
        "rows": rows,
        "o": o, "h": h, "l": l, "c": c, "v": v,
        "ta": ta,
        "score": score,
        "direction": direction,
        "adx": adx,
        "rank_score": rank_score,
    }


async def _scan_one(coin: dict[str, Any], interval: str) -> dict[str, Any] | None:
    async with _SEMAPHORE:
        try:
            pair = _pair_from_symbol(coin["symbol"])
            rows = await _fetch_klines_interval(pair, interval, 120)
            return _fast_candidate(coin, rows)
        except Exception:
            return None


def _deep_candidate(item: dict[str, Any], interval: str) -> dict[str, Any]:
    o, h, l, c, v = item["o"], item["h"], item["l"], item["c"], item["v"]
    ta = item["ta"]
    current = c[-1]
    levels = _advanced_levels(c, h, l, current)
    support = (levels.get("supports") or [{}])[0].get("price")
    resistance = (levels.get("resistances") or [{}])[0].get("price")
    pa = _price_action_analysis(o, h, l, c, v, support, resistance, ta.get("atr"))

    ict = {}
    try:
        ict = analyze_ict_from_ohlc(o, h, l, c, symbol=item["coin"]["symbol"], interval=interval)
    except Exception:
        ict = {}

    # Directional confirmation: selected timeframe + structure + ICT bias.
    bias = str(((ict.get("bias") or {}).get("direction") or "")).lower()
    final = float(item["rank_score"])
    if str(pa.get("structure") or "").startswith(item["direction"]):
        final += 4
    if (item["direction"] == "صعودی" and any(x in bias for x in ("bull", "صعود"))) or (
        item["direction"] == "نزولی" and any(x in bias for x in ("bear", "نزول"))
    ):
        final += 5

    reasons: list[str] = []
    trend = ta.get("trend")
    rsi = ta.get("rsi")
    adx = ta.get("adx")
    vr = ta.get("vol_ratio")
    if trend:
        reasons.append(f"روند {trend} با SMA20/SMA50")
    if rsi is not None:
        reasons.append(f"RSI(14)={float(rsi):.1f}")
    if adx is not None:
        reasons.append(f"ADX(14)={float(adx):.1f}")
    if vr is not None and float(vr) >= 1.15:
        reasons.append(f"حجم نسبت به میانگین ×{float(vr):.1f}")
    macd, macd_signal = ta.get("macd"), ta.get("macd_signal")
    if macd is not None and macd_signal is not None:
        reasons.append(f"MACD {'بالای' if macd > macd_signal else 'زیر'} خط سیگنال")
    stoch = ta.get("stoch")
    if stoch is not None:
        reasons.append(f"Stochastic(14)={float(stoch):.1f}")
    bb_u, bb_l = ta.get("bb_upper"), ta.get("bb_lower")
    if bb_u is not None and bb_l is not None:
        reasons.append("موقعیت قیمت نسبت به Bollinger Bands بررسی شد")
    if pa.get("structure") and pa.get("structure") != "رنج":
        reasons.append(f"ساختار قیمت: {pa['structure']}")
    if pa.get("breakout"):
        reasons.append(str(pa["breakout"]))
    if pa.get("patterns"):
        reasons.append("الگوی کندلی: " + str(pa["patterns"][-1]))
    if pa.get("chart_patterns"):
        reasons.append("الگوی نموداری: " + str(pa["chart_patterns"][0].get("name", "شناسایی‌شده")))
    if support:
        reasons.append(f"حمایت نزدیک {support:,.6g}")
    if resistance:
        reasons.append(f"مقاومت نزدیک {resistance:,.6g}")
    if ict:
        ext = (ict.get("external") or {}).get("structure") or (ict.get("external") or {}).get("phase")
        if ext:
            reasons.append(f"ICT: {ext}")
        if (ict.get("fvgs") or []):
            reasons.append("FVG شناسایی شد")
        if (ict.get("order_blocks") or []):
            reasons.append("Order Block شناسایی شد")
        if (ict.get("liquidity") or {}).get("sweeps"):
            reasons.append("Liquidity sweep شناسایی شد")

    return {
        **item,
        "final_score": round(min(100.0, final), 1),
        "label": _direction_label(item["direction"], item["score"]),
        "support": support,
        "resistance": resistance,
        "pa": pa,
        "ict": ict,
        "reasons": reasons[:6],
    }


async def scan_crypto_opportunities(interval: str) -> str:
    interval = interval if interval in TIMEFRAMES else "4h"
    tf_label, iv = TIMEFRAMES[interval]
    cache_key = f"scan:{interval}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    universe = await _top_500()
    if not universe:
        return "❌ فهرست ۵۰۰ ارز برتر فعلاً از منبع بازار دریافت نشد."

    tasks = [_scan_one(c, iv) for c in universe]
    raw = await asyncio.gather(*tasks, return_exceptions=True)
    candidates = [x for x in raw if isinstance(x, dict)]
    candidates.sort(key=lambda x: x["rank_score"], reverse=True)

    # Deep pass only on a small shortlist: this is what makes a 500-coin scan
    # practical on Render while still using Price Action + ICT on finalists.
    deep = [_deep_candidate(x, iv) for x in candidates[:18]]
    deep = [x for x in deep if x["label"] != "خنثی 🟡"]
    deep.sort(key=lambda x: x["final_score"], reverse=True)
    top = deep[:5]

    lines = [
        "🧠 <b>اسکن حرفه‌ای بازار کریپتو</b>",
        f"⏱ تایم‌فریم: <b>{tf_label} ({iv.upper()})</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"🔎 جامعه بررسی: <b>۵۰۰ ارز برتر از نظر ارزش بازار</b>",
        f"📡 داده قابل‌تحلیل: <b>{len(candidates)}</b> ارز با کندل کافی و بازار قابل‌دسترسی",
        "",
    ]

    if not top:
        lines += [
            "🟡 در این تایم‌فریم فعلاً ۵ ستاپ لانگ/شورت با کیفیت کافی پیدا نشد.",
            "این نتیجه بهتر از ساختن سیگنال مصنوعی از داده ضعیف است.",
            "",
            "⚠️ این خروجی تحلیل داده‌محور است و تضمین سود نیست.",
        ]
    else:
        for i, x in enumerate(top, 1):
            coin = x["coin"]
            price = x["c"][-1]
            lines.append(f"<b>{i}. {coin['symbol']}</b> — {coin['name']}")
            lines.append(f"   📌 {x['label']} | امتیاز تحلیل: <b>{x['final_score']:.0f}/100</b>")
            lines.append(f"   💵 قیمت: {price:,.8g} | رتبه بازار: #{coin['rank']}")
            if x.get("support") or x.get("resistance"):
                lines.append(
                    f"   🎯 حمایت: {x.get('support', '—')} | مقاومت: {x.get('resistance', '—')}"
                )
            for reason in x["reasons"][:4]:
                lines.append(f"   • {reason}")
            lines.append("")
        lines += [
            "📚 <b>روش تحلیل:</b> روند و SMA/EMA، RSI(14)، ADX(14)، ATR، MACD، Bollinger، Stochastic، حجم، ساختار بازار، "
            "الگوهای کندلی/نموداری، حمایت و مقاومت خوشه‌ای، Price Action و ICT "
            "(BOS/CHoCH، FVG، Order Block و نقدینگی).",
            "⚠️ سیگنال‌ها لحظه‌ای و آموزشی‌اند؛ قبل از معامله، قیمت و شرایط بازار را دوباره بررسی کن.",
        ]

    result = "\n".join(lines)
    _cache_put(cache_key, result)
    return result


async def handle_crypto_opportunity_callback(update, context) -> bool:
    query = update.callback_query
    data = query.data or ""
    if not data.startswith("buy:"):
        return False

    if data == "buy:menu":
        await query.answer()
        await query.edit_message_text(
            "🧠 <b>کدوم ارز بخرم؟</b>\n\n"
            "تایم‌فریم را انتخاب کن تا ۵۰۰ ارز برتر بازار اسکن شوند و ۵ ستاپ دارای "
            "سیگنال لانگ یا شورت با تحلیل عمیق‌تر نمایش داده شوند.",
            parse_mode="HTML",
            reply_markup=opportunity_timeframe_keyboard(),
        )
        return True

    if data == "buy:back":
        await query.answer()
        from bot.utils.keyboard_factory import get_market_keyboard
        await query.message.reply_text("💰 بازار:", reply_markup=get_market_keyboard())
        return True

    parts = data.split(":")
    if len(parts) != 3 or parts[1] != "scan" or parts[2] not in TIMEFRAMES:
        await query.answer("گزینه نامعتبر است.")
        return True

    interval = parts[2]
    await query.answer("⏳ اسکن ۵۰۰ ارز شروع شد…")

    # Keep Telegram typing notification alive for the whole scan duration.
    stop_event = asyncio.Event()
    chat_id = query.message.chat_id if query.message else (update.effective_chat.id if update.effective_chat else None)
    typing_task = None
    if chat_id is not None:
        typing_task = asyncio.create_task(
            _keep_typing(context.bot, chat_id, stop_event),
            name=f"opp-typing-{chat_id}",
        )

    try:
        await query.edit_message_text(
            f"⏳ <b>در حال اسکن بازار</b>\nتایم‌فریم: {TIMEFRAMES[interval][0]} ({interval.upper()})\n\n"
            "ابتدا کل جامعه ۵۰۰تایی غربال می‌شود و سپس نامزدهای برتر با Price Action و ICT عمیق‌تر بررسی می‌شوند…",
            parse_mode="HTML",
        )
        report = await scan_crypto_opportunities(interval)
        await query.edit_message_text(
            report,
            parse_mode="HTML",
            reply_markup=opportunity_timeframe_keyboard(),
        )
    except Exception as exc:
        logger.exception("crypto opportunity scan failed: %s", exc)
        try:
            await query.edit_message_text(
                "⚠️ اسکن بازار کامل نشد. داده بازار یا یکی از منابع موقتاً در دسترس نیست؛ دوباره تلاش کن.",
                reply_markup=opportunity_timeframe_keyboard(),
            )
        except Exception as edit_exc:
            logger.debug("opportunity error edit failed: %s", edit_exc)
    finally:
        stop_event.set()
        if typing_task is not None:
            try:
                await typing_task
            except Exception as _exc:
                logger.debug("opportunity typing task cleanup: %s", _exc)
    return True
