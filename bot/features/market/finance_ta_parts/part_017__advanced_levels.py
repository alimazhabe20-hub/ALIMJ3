# Auto-split part 17: _advanced_levels
def _advanced_levels(closes, highs, lows, current=None):
    """محاسبه سطوح حمایت/مقاومت خوشه‌ای بدون وابستگی به finance facade."""
    try:
        c = float(current if current is not None else closes[-1])
    except Exception:
        return {"supports": [], "resistances": []}
    if not closes or not highs or not lows:
        return {"supports": [], "resistances": []}

    vals = []
    # Pivot-like levels from recent extrema and common retracement anchors.
    n = min(len(closes), len(highs), len(lows), 120)
    hs = [float(x) for x in highs[-n:]]
    ls = [float(x) for x in lows[-n:]]
    cs = [float(x) for x in closes[-n:]]
    atr = _atr(hs, ls, cs, 14) or abs(c) * 0.01
    tol = max(atr * 0.55, abs(c) * 0.0025)

    for i in range(2, n - 2):
        if hs[i] >= max(hs[i-2:i+3]): vals.append((hs[i], "swing"))
        if ls[i] <= min(ls[i-2:i+3]): vals.append((ls[i], "swing"))
    for p in (20, 50, 100):
        if n >= p:
            vals.append((max(hs[-p:]), "range"))
            vals.append((min(ls[-p:]), "range"))
    hi, lo = max(hs), min(ls)
    if hi > lo:
        for r in (0.236, 0.382, 0.5, 0.618, 0.786):
            vals.append((hi - (hi - lo) * r, "fib"))

    clusters = []
    for price, source in sorted(vals, key=lambda x: x[0]):
        if price <= 0: continue
        found = None
        for cl in clusters:
            if abs(price - cl["price"]) <= tol:
                found = cl; break
        if found is None:
            clusters.append({"price": price, "touches": 1, "sources": {source}})
        else:
            found["price"] = (found["price"] * found["touches"] + price) / (found["touches"] + 1)
            found["touches"] += 1
            found["sources"].add(source)

    supports, resistances = [], []
    for cl in clusters:
        p = float(cl["price"])
        strength = min(100, 35 + cl["touches"] * 12 + len(cl["sources"]) * 8)
        item = {"price": p, "strength": int(strength)}
        if p < c:
            supports.append(item)
        elif p > c:
            resistances.append(item)
    supports.sort(key=lambda x: (c - x["price"]))
    resistances.sort(key=lambda x: (x["price"] - c))
    return {"supports": supports[:6], "resistances": resistances[:6]}
