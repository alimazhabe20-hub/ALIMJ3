# Auto-split part 10: _order_blocks
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
