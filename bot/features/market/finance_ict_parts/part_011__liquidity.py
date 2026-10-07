from typing import Any

# Auto-split part 11: _liquidity
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
