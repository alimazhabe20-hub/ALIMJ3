from typing import Any

# Auto-split part 12: _dealing_range
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
