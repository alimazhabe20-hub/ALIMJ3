"""finance_ict: zones responsibilities."""
from .finance_ict_common import *  # noqa: F401,F403
from . import finance_ict_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


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
