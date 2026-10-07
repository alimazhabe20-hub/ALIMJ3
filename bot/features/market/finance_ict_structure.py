"""finance_ict: structure responsibilities."""
from .finance_ict_common import *  # noqa: F401,F403
from . import finance_ict_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


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
