# Auto-split part 11: _rsi_divergence
def _rsi_divergence(closes, period: int = 14) -> str | None:
    """واگرایی ساده RSI روی ۲۰ کندل آخر"""
    if len(closes) < period + 25:
        return None
    # RSI series rough
    rsis = []
    for end in range(period + 1, len(closes) + 1):
        r = _rsi(closes[:end], period)
        if r is not None:
            rsis.append(r)
    if len(rsis) < 20:
        return None
    c = closes[-20:]
    r = rsis[-20:]
    # سقف قیمت vs RSI
    i_px_hi = max(range(len(c)), key=lambda i: c[i])
    i_rsi_hi = max(range(len(r)), key=lambda i: r[i])
    i_px_lo = min(range(len(c)), key=lambda i: c[i])
    i_rsi_lo = min(range(len(r)), key=lambda i: r[i])
    # bearish div: price higher high near end, rsi lower high
    if i_px_hi >= 12 and c[i_px_hi] >= max(c[:10]) and r[i_px_hi] < max(r[:10]) - 3:
        return "واگرایی نزولی RSI — ضعف در سقف"
    if i_px_lo >= 12 and c[i_px_lo] <= min(c[:10]) and r[i_px_lo] > min(r[:10]) + 3:
        return "واگرایی صعودی RSI — ضعف فروش در کف"
    return None
