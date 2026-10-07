# Auto-split part 13: _displacement
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
