# Auto-split part 7: _detect_candle_patterns
def _detect_candle_patterns(opens, highs, lows, closes) -> list:
    """تشخیص ساده Engulfing و Pin Bar روی آخرین کندل‌ها"""
    patterns = []
    n = len(closes)
    if n < 3 or len(opens) < n:
        return patterns
    o, h, l, c = opens[-1], highs[-1], lows[-1], closes[-1]
    po, ph, pl, pc = opens[-2], highs[-2], lows[-2], closes[-2]
    body = abs(c - o)
    range_ = max(h - l, 1e-12)
    upper = h - max(c, o)
    lower = min(c, o) - l
    prev_body = abs(pc - po)

    # Bullish Engulfing
    if pc < po and c > o and c >= po and o <= pc and body > prev_body * 0.9:
        patterns.append("پوششی صعودی (Bullish Engulfing) 🟢")
    # Bearish Engulfing
    if pc > po and c < o and c <= po and o >= pc and body > prev_body * 0.9:
        patterns.append("پوششی نزولی (Bearish Engulfing) 🔴")

    # Pin Bar / Hammer (سایه پایین بلند)
    if lower >= body * 2 and upper <= body * 0.5 and body / range_ < 0.35:
        if c >= o:
            patterns.append("پین‌بار صعودی / چکش 🟢")
        else:
            patterns.append("پین‌بار با بدنه منفی (احتیاط) 🟡")
    # Shooting Star (سایه بالا بلند)
    if upper >= body * 2 and lower <= body * 0.5 and body / range_ < 0.35:
        if c <= o:
            patterns.append("ستاره دنباله‌دار (Shooting Star) 🔴")
        else:
            patterns.append("پین‌بار معکوس (احتیاط) 🟡")

    return patterns
