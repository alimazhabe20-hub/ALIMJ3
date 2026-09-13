"""ICT (Inner Circle Trader) style market analysis.

Educational only — not financial advice.
Uses OHLCV candles (Binance/OKX via finance_ta helpers).
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from bot.logger import logger


def _f(x, default=0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def _swings(highs: list[float], lows: list[float], left: int = 2, right: int = 2) -> tuple[list, list]:
    """Fractal swings: local highs/lows."""
    sh, sl = [], []
    n = len(highs)
    for i in range(left, n - right):
        window_h = highs[i - left : i + right + 1]
        window_l = lows[i - left : i + right + 1]
        if highs[i] >= max(window_h):
            sh.append((i, highs[i]))
        if lows[i] <= min(window_l):
            sl.append((i, lows[i]))
    return sh, sl


def _detect_structure(sh: list, sl: list, close: float) -> dict:
    """HH/HL vs LH/LL, BOS, CHoCH."""
    out = {
        "trend": "رنج / نامشخص",
        "bos": None,
        "choch": None,
        "last_ssh": sh[-1][1] if sh else None,
        "last_ssl": sl[-1][1] if sl else None,
    }
    if len(sh) < 2 or len(sl) < 2:
        return out

    hh = sh[-1][1] > sh[-2][1]
    hl = sl[-1][1] > sl[-2][1]
    lh = sh[-1][1] < sh[-2][1]
    ll = sl[-1][1] < sl[-2][1]

    if hh and hl:
        out["trend"] = "صعودی (Bullish — HH/HL)"
        if close > sh[-1][1]:
            out["bos"] = f"BOS صعودی — قیمت سقف سوئینگ {sh[-1][1]:.6g} را شکست"
        # CHoCH if previous was bearish structure and broke above last LH
        if lh is False and len(sh) >= 3 and sh[-2][1] < sh[-3][1]:
            out["choch"] = "احتمال CHoCH به صعود (شکست ساختار نزولی قبلی)"
    elif lh and ll:
        out["trend"] = "نزولی (Bearish — LH/LL)"
        if close < sl[-1][1]:
            out["bos"] = f"BOS نزولی — قیمت کف سوئینگ {sl[-1][1]:.6g} را شکست"
        if len(sl) >= 3 and sl[-2][1] > sl[-3][1]:
            out["choch"] = "احتمال CHoCH به نزول (شکست ساختار صعودی قبلی)"
    elif hh and ll:
        out["trend"] = "انبساط / فشرده نیست (HH + LL)"
    elif lh and hl:
        out["trend"] = "فشردگی / احتمال CHoCH (LH + HL)"
        out["choch"] = "ساختار مختلط — مراقب تغییر جهت باشید"
    return out


def _fair_value_gaps(opens, highs, lows, closes, lookback: int = 80) -> list[dict]:
    """3-candle FVG: bullish if low[i] > high[i-2], bearish if high[i] < low[i-2]."""
    n = len(closes)
    start = max(2, n - lookback)
    fvgs = []
    for i in range(start, n):
        # Bullish FVG
        if lows[i] > highs[i - 2]:
            top, bot = lows[i], highs[i - 2]
            mid = (top + bot) / 2
            filled = closes[-1] < top  # still relevant if price not fully through
            fvgs.append({
                "type": "bullish",
                "top": top,
                "bottom": bot,
                "mid": mid,
                "index": i,
                "active": closes[-1] >= bot,
            })
        # Bearish FVG
        if highs[i] < lows[i - 2]:
            top, bot = lows[i - 2], highs[i]
            mid = (top + bot) / 2
            fvgs.append({
                "type": "bearish",
                "top": top,
                "bottom": bot,
                "mid": mid,
                "index": i,
                "active": closes[-1] <= top,
            })
    # keep last few active
    active = [g for g in fvgs if g["active"]]
    return active[-6:] if active else fvgs[-4:]


def _order_blocks(opens, highs, lows, closes, lookback: int = 60) -> list[dict]:
    """Last opposing candle before impulsive move (simplified ICT OB)."""
    n = len(closes)
    start = max(3, n - lookback)
    obs = []
    for i in range(start, n - 1):
        body = abs(closes[i] - opens[i])
        rng = max(highs[i] - lows[i], 1e-12)
        # bullish OB: down-close candle followed by strong up move
        if closes[i] < opens[i]:
            move = closes[i + 1] - opens[i + 1] if i + 1 < n else 0
            if i + 2 < n:
                impulse = max(closes[i + 1], closes[min(i + 2, n - 1)]) - highs[i]
            else:
                impulse = closes[-1] - highs[i]
            if impulse > body * 0.5 and impulse > rng * 0.3:
                obs.append({
                    "type": "bullish",
                    "high": highs[i],
                    "low": lows[i],
                    "index": i,
                    "active": closes[-1] >= lows[i] * 0.998,
                })
        # bearish OB: up-close then strong down
        if closes[i] > opens[i]:
            if i + 2 < n:
                impulse = lows[i] - min(closes[i + 1], closes[min(i + 2, n - 1)])
            else:
                impulse = lows[i] - closes[-1]
            if impulse > body * 0.5 and impulse > rng * 0.3:
                obs.append({
                    "type": "bearish",
                    "high": highs[i],
                    "low": lows[i],
                    "index": i,
                    "active": closes[-1] <= highs[i] * 1.002,
                })
    active = [o for o in obs if o["active"]]
    return active[-5:] if active else obs[-3:]


def _liquidity_pools(sh: list, sl: list, tolerance_pct: float = 0.15) -> dict:
    """Equal highs / equal lows (liquidity resting above/below)."""
    eq_h, eq_l = [], []
    for i in range(1, len(sh)):
        a, b = sh[i - 1][1], sh[i][1]
        if a and abs(a - b) / max(a, 1e-12) * 100 <= tolerance_pct:
            eq_h.append((min(a, b), max(a, b)))
    for i in range(1, len(sl)):
        a, b = sl[i - 1][1], sl[i][1]
        if a and abs(a - b) / max(a, 1e-12) * 100 <= tolerance_pct:
            eq_l.append((min(a, b), max(a, b)))
    return {
        "equal_highs": eq_h[-3:],
        "equal_lows": eq_l[-3:],
        "buy_side_liquidity": sh[-1][1] if sh else None,
        "sell_side_liquidity": sl[-1][1] if sl else None,
    }


def _liquidity_sweep(highs, lows, closes, sh, sl) -> str | None:
    """Price wicks beyond swing then closes back (stop hunt)."""
    if len(closes) < 5 or not sh or not sl:
        return None
    last_h, last_l = highs[-1], lows[-1]
    close = closes[-1]
    ssh, ssl = sh[-1][1], sl[-1][1]
    if last_h > ssh and close < ssh:
        return f"احتمال Liquidity Sweep سقف (BSL) — ویک بالای {ssh:.6g} و برگشت زیر آن"
    if last_l < ssl and close > ssl:
        return f"احتمال Liquidity Sweep کف (SSL) — ویک زیر {ssl:.6g} و برگشت بالای آن"
    return None


def _premium_discount(sh, sl, close: float) -> dict:
    """Equilibrium / premium / discount relative to last dealing range."""
    if not sh or not sl:
        return {"zone": "نامشخص", "eq": None, "range_high": None, "range_low": None}
    hi = max(p[1] for p in sh[-4:])
    lo = min(p[1] for p in sl[-4:])
    if hi <= lo:
        return {"zone": "نامشخص", "eq": None, "range_high": hi, "range_low": lo}
    eq = (hi + lo) / 2
    pos = (close - lo) / (hi - lo)
    if pos >= 0.7:
        zone = "Premium (گران — معمولاً علاقه به فروش / ادامه نزول)"
    elif pos <= 0.3:
        zone = "Discount (ارزان — معمولاً علاقه به خرید / ادامه صعود)"
    else:
        zone = "Equilibrium (تعادل)"
    # OTE band 0.62–0.79 of range from extreme in trend direction
    ote_low = lo + (hi - lo) * 0.62
    ote_high = lo + (hi - lo) * 0.79
    return {
        "zone": zone,
        "eq": eq,
        "range_high": hi,
        "range_low": lo,
        "position_pct": round(pos * 100, 1),
        "ote": (ote_low, ote_high),
    }


def _killzone_note(now: datetime | None = None) -> str:
    """Rough ICT killzones in UTC (approx)."""
    now = now or datetime.now(timezone.utc)
    h = now.hour
    # Asia 00-03, London 07-10, NY 12-15 UTC typical teaching windows
    if 0 <= h < 3:
        return "⏰ Killzone آسیا (تقریبی UTC 00–03)"
    if 7 <= h < 10:
        return "⏰ Killzone لندن (تقریبی UTC 07–10)"
    if 12 <= h < 15:
        return "⏰ Killzone نیویورک (تقریبی UTC 12–15)"
    if 15 <= h < 17:
        return "⏰ همپوشانی لندن/نیویورک (پرنوسان)"
    return "⏰ خارج از Killzoneهای اصلی ICT (UTC)"


def _displacement(opens, closes, atr: float | None) -> str | None:
    if len(closes) < 3:
        return None
    body = abs(closes[-1] - opens[-1])
    prev = abs(closes[-2] - opens[-2])
    if atr and body > atr * 1.2:
        direction = "صعودی" if closes[-1] > opens[-1] else "نزولی"
        return f"Displacement {direction} — بدنه قوی نسبت به ATR"
    if body > prev * 1.8 and body > 0:
        direction = "صعودی" if closes[-1] > opens[-1] else "نزولی"
        return f"Displacement نسبی {direction}"
    return None


def _atr(highs, lows, closes, period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    if len(trs) < period:
        return None
    return sum(trs[-period:]) / period


def analyze_ict_from_ohlc(
    opens: list[float],
    highs: list[float],
    lows: list[float],
    closes: list[float],
    *,
    symbol: str = "",
    interval: str = "1h",
) -> dict[str, Any]:
    if len(closes) < 30:
        return {"ok": False, "error": "داده کافی نیست (حداقل ۳۰ کندل)"}

    sh, sl = _swings(highs, lows)
    close = closes[-1]
    structure = _detect_structure(sh, sl, close)
    fvgs = _fair_value_gaps(opens, highs, lows, closes)
    obs = _order_blocks(opens, highs, lows, closes)
    liq = _liquidity_pools(sh, sl)
    sweep = _liquidity_sweep(highs, lows, closes, sh, sl)
    pd = _premium_discount(sh, sl, close)
    atr = _atr(highs, lows, closes)
    disp = _displacement(opens, closes, atr)

    # Bias summary
    bias = "خنثی"
    score = 0
    if structure["trend"].startswith("صعودی"):
        score += 2
    elif structure["trend"].startswith("نزولی"):
        score -= 2
    if structure.get("bos") and "صعودی" in (structure["bos"] or ""):
        score += 1
    if structure.get("bos") and "نزولی" in (structure["bos"] or ""):
        score -= 1
    if pd.get("zone", "").startswith("Discount"):
        score += 1
    if pd.get("zone", "").startswith("Premium"):
        score -= 1
    bull_fvg = sum(1 for g in fvgs if g["type"] == "bullish")
    bear_fvg = sum(1 for g in fvgs if g["type"] == "bearish")
    score += 1 if bull_fvg > bear_fvg else -1 if bear_fvg > bull_fvg else 0
    if score >= 2:
        bias = "صعودی (Bullish bias)"
    elif score <= -2:
        bias = "نزولی (Bearish bias)"

    return {
        "ok": True,
        "symbol": symbol,
        "interval": interval,
        "price": close,
        "structure": structure,
        "fvgs": fvgs,
        "order_blocks": obs,
        "liquidity": liq,
        "sweep": sweep,
        "premium_discount": pd,
        "displacement": disp,
        "atr": atr,
        "killzone": _killzone_note(),
        "bias": bias,
        "score": score,
    }


def format_ict_report(data: dict) -> str:
    if not data.get("ok"):
        return f"❌ تحلیل ICT ممکن نیست: {data.get('error', 'خطا')}"

    sym = (data.get("symbol") or "").upper()
    lines = [
        f"📐 تحلیل ICT — {sym or 'SYMBOL'} | تایم‌فریم {data.get('interval', '?')}",
        "━━━━━━━━━━━━━━━━━━━━",
        f"💵 قیمت: {data['price']:.6g}",
        f"🎯 بایاس: {data['bias']}",
        "",
        "📊 ساختار بازار (Market Structure)",
        f"• روند: {data['structure']['trend']}",
    ]
    if data["structure"].get("bos"):
        lines.append(f"• BOS: {data['structure']['bos']}")
    if data["structure"].get("choch"):
        lines.append(f"• CHoCH: {data['structure']['choch']}")
    if data["structure"].get("last_ssh"):
        lines.append(f"• آخرین سقف سوئینگ: {data['structure']['last_ssh']:.6g}")
    if data["structure"].get("last_ssl"):
        lines.append(f"• آخرین کف سوئینگ: {data['structure']['last_ssl']:.6g}")

    pd = data.get("premium_discount") or {}
    lines += [
        "",
        "⚖️ Premium / Discount",
        f"• ناحیه: {pd.get('zone', '—')}",
    ]
    if pd.get("eq") is not None:
        lines.append(f"• Equilibrium: {pd['eq']:.6g}")
        lines.append(f"• محدوده: {pd.get('range_low'):.6g} — {pd.get('range_high'):.6g}")
        lines.append(f"• موقعیت در رنج: {pd.get('position_pct')}%")
    if pd.get("ote"):
        lines.append(f"• OTE (۰٫۶۲–۰٫۷۹): {pd['ote'][0]:.6g} — {pd['ote'][1]:.6g}")

    lines += ["", "🟩 Fair Value Gap (FVG)"]
    fvgs = data.get("fvgs") or []
    if not fvgs:
        lines.append("• FVG فعالی در پنجره اخیر دیده نشد")
    else:
        for g in fvgs[-4:]:
            tag = "صعودی" if g["type"] == "bullish" else "نزولی"
            lines.append(f"• FVG {tag}: {g['bottom']:.6g} — {g['top']:.6g} (mid {g['mid']:.6g})")

    lines += ["", "📦 Order Block"]
    obs = data.get("order_blocks") or []
    if not obs:
        lines.append("• Order Block فعال مشخصی یافت نشد")
    else:
        for o in obs[-4:]:
            tag = "صعودی (Demand)" if o["type"] == "bullish" else "نزولی (Supply)"
            lines.append(f"• OB {tag}: {o['low']:.6g} — {o['high']:.6g}")

    liq = data.get("liquidity") or {}
    lines += ["", "💧 نقدینگی (Liquidity)"]
    if liq.get("buy_side_liquidity"):
        lines.append(f"• BSL (بالای سقف): {liq['buy_side_liquidity']:.6g}")
    if liq.get("sell_side_liquidity"):
        lines.append(f"• SSL (زیر کف): {liq['sell_side_liquidity']:.6g}")
    if liq.get("equal_highs"):
        lines.append(f"• Equal Highs: {len(liq['equal_highs'])} مورد")
    if liq.get("equal_lows"):
        lines.append(f"• Equal Lows: {len(liq['equal_lows'])} مورد")
    if data.get("sweep"):
        lines.append(f"• {data['sweep']}")

    if data.get("displacement"):
        lines += ["", f"⚡ {data['displacement']}"]
    if data.get("atr"):
        lines.append(f"📏 ATR(14): {data['atr']:.6g}")

    lines += [
        "",
        data.get("killzone") or "",
        "",
        "⚠️ صرفاً آموزشی است و توصیه مالی / سیگنال قطعی نیست.",
        "قبل از هر تصمیم، ساختار را روی چارت خودت تأیید کن.",
    ]
    return "\n".join(lines)


async def analyze_ict(symbol: str, interval: str = "1h", limit: int = 200) -> str:
    """Fetch candles and return Persian ICT report."""
    from bot.features.market.finance_ta import _fetch_klines_for_ta
    from bot.features.market import finance as fin

    sym = (symbol or "btc").lower().strip()
    for junk in ("تحلیل", "ict", "آی‌سی‌تی", "اسیتی", "usdt", "تحلیل ict"):
        sym = sym.replace(junk, "")
    sym = sym.strip() or "btc"

    pair = f"{sym.upper()}USDT"
    if sym in ("gold", "xau", "xauusd"):
        pair = "PAXGUSDT"  # proxy if available; else BTC
        sym = "xau"

    klines = []
    try:
        # Map friendly interval to exchange format
        iv = {
            "15m": "15m", "15": "15m",
            "1h": "1h", "60m": "1h",
            "4h": "4h",
            "1d": "1d", "1day": "1d", "daily": "1d",
        }.get((interval or "1h").lower(), "1h")
        if hasattr(fin, "_fetch_klines_interval"):
            klines = await fin._fetch_klines_interval(pair, iv, int(limit))
        if not klines:
            klines = await _fetch_klines_for_ta(pair, limit=limit)
            iv = "1h"
        interval = iv
    except Exception as e:
        logger.warning("ICT klines failed: %s", e)
        klines = []

    if not klines or len(klines) < 30:
        return (
            f"❌ داده کندل برای {sym.upper()} پیدا نشد.\n"
            "نماد را مثل btc / eth / sol بفرستید."
        )

    opens = [_f(k[1]) for k in klines]
    highs = [_f(k[2]) for k in klines]
    lows = [_f(k[3]) for k in klines]
    closes = [_f(k[4]) for k in klines]

    data = analyze_ict_from_ohlc(
        opens, highs, lows, closes, symbol=sym, interval=interval
    )
    return format_ict_report(data)
