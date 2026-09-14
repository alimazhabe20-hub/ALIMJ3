# Auto-split part 9: _fair_value_gaps
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
