"""Professional ICT (Inner Circle Trader) analysis engine.

Concepts covered (educational implementation):
  - Swing points (strength-weighted fractals)
  - External market structure: HH/HL/LH/LL, BOS, MSS/CHoCH
  - Internal structure (shorter swing length)
  - Fair Value Gaps + CE (50%) + partial fill state
  - Order Blocks, Breaker Blocks, mitigation status
  - Liquidity: BSL/SSL, equal highs/lows, sweeps / stop-runs
  - Dealing range → Premium / Discount / Equilibrium + OTE (0.62–0.79)
  - Displacement (impulse) quality vs ATR
  - Session killzones (UTC)
  - Multi-timeframe bias blend when higher TF data is available
  - Confidence-weighted directional bias

Not financial advice.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bot.logger import logger


# ── utils ──────────────────────────────────────────────────────────────────

def _f(x, default: float = 0.0) -> float:
    try:
        v = float(x)
        if v != v:  # NaN
            return default
        return v
    except Exception:
        return default


def _pct(a: float, b: float) -> float:
    if not b:
        return 0.0
    return abs(a - b) / abs(b) * 100.0


def _atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> float | None:
    if len(closes) < period + 2:
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


def _body(o: float, c: float) -> float:
    return abs(c - o)


def _range(h: float, l: float) -> float:
    return max(h - l, 1e-12)


# ── swings ─────────────────────────────────────────────────────────────────

def _swings(
    highs: list[float],
    lows: list[float],
    left: int = 3,
    right: int = 3,
) -> tuple[list[tuple[int, float]], list[tuple[int, float]]]:
    """Confirmed fractal swings (need `right` bars after pivot)."""
    sh: list[tuple[int, float]] = []
    sl: list[tuple[int, float]] = []
    n = len(highs)
    if n < left + right + 1:
        return sh, sl
    for i in range(left, n - right):
        h_win = highs[i - left : i + right + 1]
        l_win = lows[i - left : i + right + 1]
        if highs[i] >= max(h_win) - 1e-12:
            # unique peak in window
            if list(h_win).count(highs[i]) == 1 or highs[i] == max(h_win):
                sh.append((i, highs[i]))
        if lows[i] <= min(l_win) + 1e-12:
            if list(l_win).count(lows[i]) == 1 or lows[i] == min(l_win):
                sl.append((i, lows[i]))
    return sh, sl


def _swing_strength(
    idx: int,
    price: float,
    highs: list[float],
    lows: list[float],
    mode: str,
    atr: float | None,
) -> float:
    """0–100 rough strength: range vs ATR + isolation."""
    left = max(0, idx - 5)
    right = min(len(highs), idx + 6)
    if mode == "high":
        span = price - min(lows[left:right])
    else:
        span = max(highs[left:right]) - price
    if atr and atr > 0:
        return max(0.0, min(100.0, (span / atr) * 35.0))
    return 50.0


# ── market structure ───────────────────────────────────────────────────────

def _structure_from_swings(
    sh: list[tuple[int, float]],
    sl: list[tuple[int, float]],
    close: float,
    label: str = "external",
) -> dict[str, Any]:
    """
    BOS = continuation break of structure in trend direction.
    MSS/CHoCH = break against prior trend (shift).
    """
    out: dict[str, Any] = {
        "label": label,
        "trend": "رنج / نامشخص",
        "phase": "neutral",
        "bos": None,
        "mss": None,
        "last_high": sh[-1][1] if sh else None,
        "last_low": sl[-1][1] if sl else None,
        "prev_high": sh[-2][1] if len(sh) >= 2 else None,
        "prev_low": sl[-2][1] if len(sl) >= 2 else None,
        "events": [],
    }
    if len(sh) < 2 or len(sl) < 2:
        return out

    # Character of last two swing pairs
    hh = sh[-1][1] > sh[-2][1]
    hl = sl[-1][1] > sl[-2][1]
    lh = sh[-1][1] < sh[-2][1]
    ll = sl[-1][1] < sl[-2][1]

    prior_bull = False
    prior_bear = False
    if len(sh) >= 3 and len(sl) >= 3:
        prior_bull = sh[-2][1] > sh[-3][1] and sl[-2][1] > sl[-3][1]
        prior_bear = sh[-2][1] < sh[-3][1] and sl[-2][1] < sl[-3][1]

    if hh and hl:
        out["trend"] = "صعودی (Bullish HH/HL)"
        out["phase"] = "bullish"
        if close > sh[-1][1]:
            out["bos"] = {
                "side": "bullish",
                "level": sh[-1][1],
                "text": f"BOS صعودی — شکست سقف سوئینگ {sh[-1][1]:.6g}",
            }
            out["events"].append(out["bos"]["text"])
        if prior_bear and close > sh[-2][1]:
            out["mss"] = {
                "side": "bullish",
                "level": sh[-2][1],
                "text": f"MSS/CHoCH صعودی — شکست ساختار نزولی در {sh[-2][1]:.6g}",
            }
            out["events"].append(out["mss"]["text"])
    elif lh and ll:
        out["trend"] = "نزولی (Bearish LH/LL)"
        out["phase"] = "bearish"
        if close < sl[-1][1]:
            out["bos"] = {
                "side": "bearish",
                "level": sl[-1][1],
                "text": f"BOS نزولی — شکست کف سوئینگ {sl[-1][1]:.6g}",
            }
            out["events"].append(out["bos"]["text"])
        if prior_bull and close < sl[-2][1]:
            out["mss"] = {
                "side": "bearish",
                "level": sl[-2][1],
                "text": f"MSS/CHoCH نزولی — شکست ساختار صعودی در {sl[-2][1]:.6g}",
            }
            out["events"].append(out["mss"]["text"])
    elif hh and ll:
        out["trend"] = "انبساط (HH+LL) — نوسان در حال گسترش"
        out["phase"] = "expanding"
    elif lh and hl:
        out["trend"] = "فشردگی (LH+HL) — احتمال MSS"
        out["phase"] = "contracting"
        out["mss"] = {
            "side": "mixed",
            "level": close,
            "text": "ساختار مختلط — منتظر تأیید BOS/MSS بمانید",
        }
    return out


# ── FVG ────────────────────────────────────────────────────────────────────

def _fair_value_gaps(
    opens: list[float],
    highs: list[float],
    lows: list[float],
    closes: list[float],
    lookback: int = 120,
    atr: float | None = None,
) -> list[dict]:
    """
    Classic 3-candle imbalance:
      Bullish FVG: low[i] > high[i-2]
      Bearish FVG: high[i] < low[i-2]
    CE = midpoint. Size filtered vs ATR when available.
    """
    n = len(closes)
    start = max(2, n - lookback)
    gaps: list[dict] = []
    min_size = (atr * 0.15) if atr else 0.0

    for i in range(start, n):
        # Bullish
        if lows[i] > highs[i - 2]:
            top, bot = lows[i], highs[i - 2]
            size = top - bot
            if size < min_size:
                continue
            ce = (top + bot) / 2
            # fill state vs current price
            if closes[-1] <= bot:
                state = "filled"
            elif closes[-1] < top:
                state = "partial" if closes[-1] <= ce else "open"
            else:
                state = "open"
            gaps.append({
                "type": "bullish",
                "top": top,
                "bottom": bot,
                "ce": ce,
                "size": size,
                "index": i,
                "state": state,
                "age": n - 1 - i,
            })
        # Bearish
        if highs[i] < lows[i - 2]:
            top, bot = lows[i - 2], highs[i]
            size = top - bot
            if size < min_size:
                continue
            ce = (top + bot) / 2
            if closes[-1] >= top:
                state = "filled"
            elif closes[-1] > bot:
                state = "partial" if closes[-1] >= ce else "open"
            else:
                state = "open"
            gaps.append({
                "type": "bearish",
                "top": top,
                "bottom": bot,
                "ce": ce,
                "size": size,
                "index": i,
                "state": state,
                "age": n - 1 - i,
            })

    # Prefer open/partial, nearest to price
    price = closes[-1]
    def rank(g: dict) -> tuple:
        dist = min(abs(price - g["top"]), abs(price - g["bottom"]), abs(price - g["ce"]))
        state_rank = {"open": 0, "partial": 1, "filled": 2}.get(g["state"], 3)
        return (state_rank, dist, g["age"])

    gaps.sort(key=rank)
    # return up to 8 most relevant
    return gaps[:8]


# ── Order blocks / breakers ────────────────────────────────────────────────

def _order_blocks(
    opens: list[float],
    highs: list[float],
    lows: list[float],
    closes: list[float],
    atr: float | None = None,
    lookback: int = 80,
) -> list[dict]:
    """
    Last opposing candle before displacement.
    Mitigation: price traded back into OB zone.
    Breaker: OB broken through decisively → flips role.
    """
    n = len(closes)
    start = max(4, n - lookback)
    min_impulse = (atr * 0.8) if atr else None
    blocks: list[dict] = []

    for i in range(start, n - 2):
        o, h, l, c = opens[i], highs[i], lows[i], closes[i]
        body = _body(o, c)
        rng = _range(h, l)
        # measure impulse over next 1–3 candles
        future_high = max(highs[i + 1 : min(i + 4, n)])
        future_low = min(lows[i + 1 : min(i + 4, n)])

        # Bullish OB: down/bearish candle then upside displacement
        if c < o:
            impulse = future_high - h
            if impulse <= body * 0.4:
                continue
            if min_impulse and impulse < min_impulse * 0.5:
                continue
            if impulse < rng * 0.25:
                continue
            mitigated = any(lows[j] <= h and highs[j] >= l for j in range(i + 1, n))
            broken = closes[-1] < l  # closed below OB → potential breaker
            role = "breaker_bearish" if broken else "bullish_ob"
            blocks.append({
                "type": role,
                "side": "bullish",
                "high": h,
                "low": l,
                "open": o,
                "close": c,
                "index": i,
                "impulse": impulse,
                "mitigated": mitigated,
                "broken": broken,
                "mid": (h + l) / 2,
            })

        # Bearish OB: up/bullish candle then downside displacement
        if c > o:
            impulse = l - future_low
            if impulse <= body * 0.4:
                continue
            if min_impulse and impulse < min_impulse * 0.5:
                continue
            if impulse < rng * 0.25:
                continue
            mitigated = any(highs[j] >= l and lows[j] <= h for j in range(i + 1, n))
            broken = closes[-1] > h
            role = "breaker_bullish" if broken else "bearish_ob"
            blocks.append({
                "type": role,
                "side": "bearish",
                "high": h,
                "low": l,
                "open": o,
                "close": c,
                "index": i,
                "impulse": impulse,
                "mitigated": mitigated,
                "broken": broken,
                "mid": (h + l) / 2,
            })

    price = closes[-1]
    def rank(b: dict) -> tuple:
        # active (not broken) first, then nearest
        dist = min(abs(price - b["high"]), abs(price - b["low"]))
        return (1 if b["broken"] else 0, 1 if b["mitigated"] else 0, dist)

    blocks.sort(key=rank)
    return blocks[:8]


# ── liquidity ──────────────────────────────────────────────────────────────

def _liquidity(
    sh: list[tuple[int, float]],
    sl: list[tuple[int, float]],
    highs: list[float],
    lows: list[float],
    closes: list[float],
    eq_tol_pct: float = 0.12,
) -> dict[str, Any]:
    eq_h: list[tuple[float, float]] = []
    eq_l: list[tuple[float, float]] = []
    for i in range(1, len(sh)):
        a, b = sh[i - 1][1], sh[i][1]
        if _pct(a, b) <= eq_tol_pct:
            eq_h.append((min(a, b), max(a, b)))
    for i in range(1, len(sl)):
        a, b = sl[i - 1][1], sl[i][1]
        if _pct(a, b) <= eq_tol_pct:
            eq_l.append((min(a, b), max(a, b)))

    bsl = sh[-1][1] if sh else None  # buy-side liquidity above highs
    ssl = sl[-1][1] if sl else None

    sweep = None
    if sh and sl and len(highs) >= 2:
        # wick beyond then close back inside
        if highs[-1] > sh[-1][1] and closes[-1] < sh[-1][1]:
            depth = highs[-1] - sh[-1][1]
            sweep = {
                "side": "bsl",
                "level": sh[-1][1],
                "depth": depth,
                "text": f"Sweep سقف (BSL) — ویک تا {highs[-1]:.6g} و کلوز زیر {sh[-1][1]:.6g}",
            }
        elif lows[-1] < sl[-1][1] and closes[-1] > sl[-1][1]:
            depth = sl[-1][1] - lows[-1]
            sweep = {
                "side": "ssl",
                "level": sl[-1][1],
                "depth": depth,
                "text": f"Sweep کف (SSL) — ویک تا {lows[-1]:.6g} و کلوز بالای {sl[-1][1]:.6g}",
            }

    return {
        "equal_highs": eq_h[-4:],
        "equal_lows": eq_l[-4:],
        "bsl": bsl,
        "ssl": ssl,
        "sweep": sweep,
    }


# ── dealing range / premium-discount / OTE ─────────────────────────────────

def _dealing_range(
    sh: list[tuple[int, float]],
    sl: list[tuple[int, float]],
    closes: list[float],
    phase: str,
) -> dict[str, Any]:
    """
    Use last meaningful swing high/low as dealing range.
    OTE: 61.8%–79% retracement of the impulse leg (ICT teaching).
    """
    if not sh or not sl:
        return {"zone": "نامشخص", "eq": None}

    # Prefer most recent swing high & low forming the active range
    hi = sh[-1][1]
    lo = sl[-1][1]
    # If last high is older than last low or vice versa, still use pair
    if len(sh) >= 2 and len(sl) >= 2:
        # dealing range from last impulse: higher of last two highs vs lower of last two lows
        hi = max(sh[-1][1], sh[-2][1])
        lo = min(sl[-1][1], sl[-2][1])

    if hi <= lo:
        return {"zone": "نامشخص", "eq": None, "high": hi, "low": lo}

    eq = (hi + lo) / 2
    close = closes[-1]
    pos = (close - lo) / (hi - lo)
    pos = max(0.0, min(1.0, pos))

    if pos >= 0.7:
        zone = "Premium"
        zone_fa = "Premium (گران — ناحیه عرضه نسبی)"
    elif pos <= 0.3:
        zone = "Discount"
        zone_fa = "Discount (ارزان — ناحیه تقاضا نسبی)"
    else:
        zone = "Equilibrium"
        zone_fa = "Equilibrium (تعادل)"

    # OTE relative to bullish impulse (low→high) and bearish (high→low)
    # Bullish OTE: retrace from high toward low into 62–79% from high
    bull_ote_hi = hi - (hi - lo) * 0.62
    bull_ote_lo = hi - (hi - lo) * 0.79
    # Bearish OTE: retrace from low toward high into 62–79% from low
    bear_ote_lo = lo + (hi - lo) * 0.62
    bear_ote_hi = lo + (hi - lo) * 0.79

    in_bull_ote = bull_ote_lo <= close <= bull_ote_hi
    in_bear_ote = bear_ote_lo <= close <= bear_ote_hi

    return {
        "zone": zone,
        "zone_fa": zone_fa,
        "eq": eq,
        "high": hi,
        "low": lo,
        "position_pct": round(pos * 100.0, 1),
        "bull_ote": (min(bull_ote_lo, bull_ote_hi), max(bull_ote_lo, bull_ote_hi)),
        "bear_ote": (min(bear_ote_lo, bear_ote_hi), max(bear_ote_lo, bear_ote_hi)),
        "in_bull_ote": in_bull_ote,
        "in_bear_ote": in_bear_ote,
    }


# ── displacement ───────────────────────────────────────────────────────────

def _displacement(
    opens: list[float],
    highs: list[float],
    lows: list[float],
    closes: list[float],
    atr: float | None,
) -> dict | None:
    if len(closes) < 4:
        return None
    body = _body(opens[-1], closes[-1])
    rng = _range(highs[-1], lows[-1])
    prev_bodies = [_body(opens[i], closes[i]) for i in range(-4, -1)]
    avg_prev = sum(prev_bodies) / max(len(prev_bodies), 1)
    side = "bullish" if closes[-1] > opens[-1] else "bearish"
    score = 0.0
    if atr and atr > 0:
        score += min(3.0, body / atr)
    if avg_prev > 0:
        score += min(2.0, body / avg_prev)
    if body / rng >= 0.65:
        score += 1.0
    if score < 2.0:
        return None
    return {
        "side": side,
        "body": body,
        "score": round(score, 2),
        "text": f"Displacement {'صعودی' if side == 'bullish' else 'نزولی'} (قدرت {score:.1f})",
    }


# ── killzones ──────────────────────────────────────────────────────────────

def _killzone(now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    h, m = now.hour, now.minute
    t = h + m / 60.0
    # Approximate ICT windows in UTC (standard teaching, not DST-perfect)
    zones = [
        (0.0, 3.0, "Asia", "آسیا"),
        (7.0, 10.0, "London", "لندن"),
        (12.0, 15.0, "New York", "نیویورک AM"),
        (15.0, 17.0, "NY Lunch / overlap", "همپوشانی لندن–نیویورک"),
        (19.0, 22.0, "New York PM", "نیویورک PM"),
    ]
    active = []
    for a, b, en, fa in zones:
        if a <= t < b:
            active.append(fa)
    return {
        "utc": now.strftime("%H:%M UTC"),
        "active": active,
        "text": (
            "⏰ Killzone فعال: " + "، ".join(active)
            if active
            else f"⏰ خارج از Killzoneهای اصلی ({now.strftime('%H:%M')} UTC)"
        ),
    }


# ── bias engine ────────────────────────────────────────────────────────────

def _compute_bias(
    ext: dict,
    internal: dict,
    fvgs: list,
    obs: list,
    liq: dict,
    dr: dict,
    disp: dict | None,
) -> dict:
    score = 0.0
    reasons: list[str] = []

    if ext.get("phase") == "bullish":
        score += 2.5
        reasons.append("ساختار خارجی صعودی")
    elif ext.get("phase") == "bearish":
        score -= 2.5
        reasons.append("ساختار خارجی نزولی")

    if ext.get("bos"):
        if ext["bos"]["side"] == "bullish":
            score += 1.5
            reasons.append("BOS صعودی")
        else:
            score -= 1.5
            reasons.append("BOS نزولی")
    if ext.get("mss"):
        if ext["mss"].get("side") == "bullish":
            score += 2.0
            reasons.append("MSS صعودی")
        elif ext["mss"].get("side") == "bearish":
            score -= 2.0
            reasons.append("MSS نزولی")

    if internal.get("phase") == "bullish":
        score += 0.8
    elif internal.get("phase") == "bearish":
        score -= 0.8

    open_bull = sum(1 for g in fvgs if g["type"] == "bullish" and g["state"] in ("open", "partial"))
    open_bear = sum(1 for g in fvgs if g["type"] == "bearish" and g["state"] in ("open", "partial"))
    if open_bull > open_bear:
        score += 0.7
        reasons.append("FVGهای صعودی فعال‌تر")
    elif open_bear > open_bull:
        score -= 0.7
        reasons.append("FVGهای نزولی فعال‌تر")

    bull_ob = sum(1 for b in obs if b["side"] == "bullish" and not b["broken"])
    bear_ob = sum(1 for b in obs if b["side"] == "bearish" and not b["broken"])
    if bull_ob > bear_ob:
        score += 0.5
    elif bear_ob > bull_ob:
        score -= 0.5

    if dr.get("zone") == "Discount":
        score += 1.0
        reasons.append("قیمت در Discount")
    elif dr.get("zone") == "Premium":
        score -= 1.0
        reasons.append("قیمت در Premium")

    if dr.get("in_bull_ote"):
        score += 0.8
        reasons.append("داخل OTE صعودی")
    if dr.get("in_bear_ote"):
        score -= 0.8
        reasons.append("داخل OTE نزولی")

    sweep = liq.get("sweep")
    if sweep:
        if sweep["side"] == "ssl":
            score += 1.2
            reasons.append("Sweep کف (جذب نقدینگی فروش)")
        elif sweep["side"] == "bsl":
            score -= 1.2
            reasons.append("Sweep سقف (جذب نقدینگی خرید)")

    if disp:
        if disp["side"] == "bullish":
            score += min(1.5, disp["score"] * 0.35)
            reasons.append(disp["text"])
        else:
            score -= min(1.5, disp["score"] * 0.35)
            reasons.append(disp["text"])

    # confidence from |score| and agreement
    conf = min(95.0, 40.0 + abs(score) * 8.0)
    if ext.get("phase") in ("bullish", "bearish") and internal.get("phase") == ext.get("phase"):
        conf = min(95.0, conf + 8.0)
        reasons.append("هم‌راستایی ساختار داخلی و خارجی")

    if score >= 2.5:
        bias = "صعودی قوی (Strong Bullish)"
        side = "bullish"
    elif score >= 1.0:
        bias = "صعودی ملایم (Mild Bullish)"
        side = "bullish"
    elif score <= -2.5:
        bias = "نزولی قوی (Strong Bearish)"
        side = "bearish"
    elif score <= -1.0:
        bias = "نزولی ملایم (Mild Bearish)"
        side = "bearish"
    else:
        bias = "خنثی / منتظر تأیید (Neutral)"
        side = "neutral"
        conf = min(conf, 55.0)

    return {
        "bias": bias,
        "side": side,
        "score": round(score, 2),
        "confidence": round(conf, 1),
        "reasons": reasons[:8],
    }


# ── scenario notes ─────────────────────────────────────────────────────────

def _scenarios(bias: dict, dr: dict, liq: dict, ext: dict) -> list[str]:
    notes = []
    side = bias.get("side")
    if side == "bullish":
        notes.append(
            "سناریو صعودی: حفظ ساختار HH/HL، برگشت از Discount/OTE یا FVG صعودی، "
            "با هدف نقدینگی بالای BSL."
        )
        if liq.get("bsl"):
            notes.append(f"هدف نقدینگی بالقوه (BSL): {liq['bsl']:.6g}")
        if ext.get("last_low"):
            notes.append(f"نقض سناریو: کلوز پایدار زیر {ext['last_low']:.6g}")
    elif side == "bearish":
        notes.append(
            "سناریو نزولی: حفظ LH/LL، برگشت از Premium/OTE یا FVG نزولی، "
            "با هدف نقدینگی زیر SSL."
        )
        if liq.get("ssl"):
            notes.append(f"هدف نقدینگی بالقوه (SSL): {liq['ssl']:.6g}")
        if ext.get("last_high"):
            notes.append(f"نقض سناریو: کلوز پایدار بالای {ext['last_high']:.6g}")
    else:
        notes.append(
            "سناریو خنثی: تا BOS/MSS واضح یا ورود قیمت به OTE همراه با Displacement، "
            "از ورود عجولانه خودداری کنید."
        )
    return notes


# ── core ───────────────────────────────────────────────────────────────────

def analyze_ict_from_ohlc(
    opens: list[float],
    highs: list[float],
    lows: list[float],
    closes: list[float],
    *,
    symbol: str = "",
    interval: str = "1h",
) -> dict[str, Any]:
    n = len(closes)
    if n < 40:
        return {"ok": False, "error": "داده کافی نیست (حداقل ۴۰ کندل لازم است)"}

    opens = [_f(x) for x in opens]
    highs = [_f(x) for x in highs]
    lows = [_f(x) for x in lows]
    closes = [_f(x) for x in closes]

    atr = _atr(highs, lows, closes)
    # External swings (stronger) vs internal (tighter)
    sh_ext, sl_ext = _swings(highs, lows, left=4, right=4)
    sh_int, sl_int = _swings(highs, lows, left=2, right=2)

    ext = _structure_from_swings(sh_ext, sl_ext, closes[-1], "external")
    internal = _structure_from_swings(sh_int, sl_int, closes[-1], "internal")
    fvgs = _fair_value_gaps(opens, highs, lows, closes, atr=atr)
    obs = _order_blocks(opens, highs, lows, closes, atr=atr)
    liq = _liquidity(sh_ext, sl_ext, highs, lows, closes)
    dr = _dealing_range(sh_ext, sl_ext, closes, ext.get("phase") or "neutral")
    disp = _displacement(opens, highs, lows, closes, atr)
    kz = _killzone()
    bias = _compute_bias(ext, internal, fvgs, obs, liq, dr, disp)
    scenarios = _scenarios(bias, dr, liq, ext)

    return {
        "ok": True,
        "symbol": symbol,
        "interval": interval,
        "price": closes[-1],
        "atr": atr,
        "candles": n,
        "external": ext,
        "internal": internal,
        "fvgs": fvgs,
        "order_blocks": obs,
        "liquidity": liq,
        "dealing_range": dr,
        "displacement": disp,
        "killzone": kz,
        "bias": bias,
        "scenarios": scenarios,
        "swings": {
            "ext_highs": sh_ext[-5:],
            "ext_lows": sl_ext[-5:],
        },
    }


def format_ict_report(data: dict) -> str:
    if not data.get("ok"):
        return f"❌ تحلیل ICT ممکن نیست: {data.get('error', 'خطا')}"

    sym = (data.get("symbol") or "").upper()
    b = data["bias"]
    ext = data["external"]
    internal = data["internal"]
    dr = data["dealing_range"]
    liq = data["liquidity"]
    kz = data["killzone"]

    lines = [
        f"📐 تحلیل ICT حرفه‌ای — {sym or 'SYMBOL'}",
        f"⏱ تایم‌فریم: {data.get('interval')} | کندل‌ها: {data.get('candles')}",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        f"💵 قیمت: {data['price']:.6g}",
        f"🎯 بایاس: {b['bias']}",
        f"📊 امتیاز: {b['score']:+.2f}  |  اطمینان: {b['confidence']:.0f}%",
        "",
        "🔹 ساختار خارجی (External)",
        f"• {ext['trend']}",
    ]
    if ext.get("bos"):
        lines.append(f"• {ext['bos']['text']}")
    if ext.get("mss"):
        lines.append(f"• {ext['mss']['text']}")
    if ext.get("last_high") is not None:
        lines.append(f"• سقف سوئینگ: {ext['last_high']:.6g}")
    if ext.get("last_low") is not None:
        lines.append(f"• کف سوئینگ: {ext['last_low']:.6g}")

    lines += [
        "",
        "🔸 ساختار داخلی (Internal)",
        f"• {internal['trend']}",
    ]
    if internal.get("bos"):
        lines.append(f"• {internal['bos']['text']}")
    if internal.get("mss"):
        lines.append(f"• {internal['mss']['text']}")

    lines += ["", "⚖️ Dealing Range / Premium–Discount"]
    lines.append(f"• {dr.get('zone_fa') or dr.get('zone')}")
    if dr.get("eq") is not None:
        lines.append(f"• High: {dr['high']:.6g}  |  EQ: {dr['eq']:.6g}  |  Low: {dr['low']:.6g}")
        lines.append(f"• موقعیت در رنج: {dr.get('position_pct')}%")
    if dr.get("bull_ote"):
        lo, hi = dr["bull_ote"]
        mark = " ✅" if dr.get("in_bull_ote") else ""
        lines.append(f"• OTE صعودی (۶۲–۷۹٪): {lo:.6g} — {hi:.6g}{mark}")
    if dr.get("bear_ote"):
        lo, hi = dr["bear_ote"]
        mark = " ✅" if dr.get("in_bear_ote") else ""
        lines.append(f"• OTE نزولی (۶۲–۷۹٪): {lo:.6g} — {hi:.6g}{mark}")

    lines += ["", "🟩 Fair Value Gaps"]
    fvgs = data.get("fvgs") or []
    if not fvgs:
        lines.append("• FVG مرتبطی در پنجره اخیر نیست")
    else:
        for g in fvgs[:5]:
            side = "صعودی" if g["type"] == "bullish" else "نزولی"
            st = {"open": "باز", "partial": "نیمه‌پر", "filled": "پرشده"}.get(g["state"], g["state"])
            lines.append(
                f"• FVG {side} [{st}]: {g['bottom']:.6g}—{g['top']:.6g} "
                f"| CE {g['ce']:.6g} | عمر {g['age']} کندل"
            )

    lines += ["", "📦 Order Block / Breaker"]
    obs = data.get("order_blocks") or []
    if not obs:
        lines.append("• OB معتبری در پنجره اخیر نیست")
    else:
        for o in obs[:5]:
            if o["type"] == "bullish_ob":
                tag = "Demand OB"
            elif o["type"] == "bearish_ob":
                tag = "Supply OB"
            elif o["type"] == "breaker_bearish":
                tag = "Breaker↓ (OB صعودی شکسته‌شده)"
            else:
                tag = "Breaker↑ (OB نزولی شکسته‌شده)"
            flags = []
            if o.get("mitigated"):
                flags.append("mitigated")
            if o.get("broken"):
                flags.append("broken")
            flag_s = f" [{', '.join(flags)}]" if flags else ""
            lines.append(f"• {tag}: {o['low']:.6g}—{o['high']:.6g}{flag_s}")

    lines += ["", "💧 نقدینگی"]
    if liq.get("bsl") is not None:
        lines.append(f"• BSL (بالای سقف): {liq['bsl']:.6g}")
    if liq.get("ssl") is not None:
        lines.append(f"• SSL (زیر کف): {liq['ssl']:.6g}")
    if liq.get("equal_highs"):
        lines.append(f"• Equal Highs: {len(liq['equal_highs'])} خوشه")
    if liq.get("equal_lows"):
        lines.append(f"• Equal Lows: {len(liq['equal_lows'])} خوشه")
    if liq.get("sweep"):
        lines.append(f"• {liq['sweep']['text']}")

    if data.get("displacement"):
        lines += ["", f"⚡ {data['displacement']['text']}"]
    if data.get("atr"):
        lines.append(f"📏 ATR(14): {data['atr']:.6g}")

    lines += ["", kz.get("text", "")]

    if b.get("reasons"):
        lines += ["", "🧠 دلایل بایاس"]
        for r in b["reasons"]:
            lines.append(f"• {r}")

    if data.get("scenarios"):
        lines += ["", "📋 سناریوها"]
        for s in data["scenarios"]:
            lines.append(f"• {s}")

    lines += [
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "⚠️ صرفاً آموزشی است — توصیه مالی یا سیگنال قطعی نیست.",
        "ورود فقط با تأیید شخصی روی چارت و مدیریت ریسک.",
    ]
    return "\n".join(lines)


async def analyze_ict(symbol: str, interval: str = "1h", limit: int = 250) -> str:
    """Fetch OHLCV and return professional Persian ICT report."""
    from bot.features.market.finance_ta import _fetch_klines_for_ta
    from bot.features.market import finance as fin

    raw = (symbol or "btc").lower().strip()
    for junk in (
        "تحلیل", "ict", "آی‌سی‌تی", "اسیتی", "usdt", "تحلیل ict",
        "به روش", "روش",
    ):
        raw = raw.replace(junk, "")
    raw = raw.strip() or "btc"
    parts = raw.split()
    sym = parts[0]
    if len(parts) > 1 and parts[1] in ("15m", "15", "1h", "4h", "1d", "h1", "h4", "daily"):
        interval = parts[1]

    iv = {
        "15": "15m", "15m": "15m",
        "1h": "1h", "h1": "1h", "60m": "1h",
        "4h": "4h", "h4": "4h",
        "1d": "1d", "1day": "1d", "daily": "1d",
    }.get((interval or "1h").lower(), "1h")

    pair = f"{sym.upper()}USDT"
    if sym in ("gold", "xau", "xauusd"):
        pair = "PAXGUSDT"
        sym = "xau"

    klines: list = []
    try:
        if hasattr(fin, "_fetch_klines_interval"):
            klines = await fin._fetch_klines_interval(pair, iv, int(limit))
        if not klines:
            klines = await _fetch_klines_for_ta(pair, limit=limit)
            iv = "1h"
    except Exception as e:
        logger.warning("ICT klines failed: %s", e)

    if not klines or len(klines) < 40:
        return (
            f"❌ داده کندل کافی برای {sym.upper()} یافت نشد.\n"
            "مثال: btc | eth 4h | sol 1h | btc 15m"
        )

    opens = [_f(k[1]) for k in klines]
    highs = [_f(k[2]) for k in klines]
    lows = [_f(k[3]) for k in klines]
    closes = [_f(k[4]) for k in klines]

    data = analyze_ict_from_ohlc(
        opens, highs, lows, closes, symbol=sym, interval=iv
    )
    return format_ict_report(data)
