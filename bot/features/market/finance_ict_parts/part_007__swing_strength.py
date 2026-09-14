# Auto-split part 7: _swing_strength
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
