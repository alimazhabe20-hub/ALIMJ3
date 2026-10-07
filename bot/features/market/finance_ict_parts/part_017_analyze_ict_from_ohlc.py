from typing import Any

# Auto-split part 17: analyze_ict_from_ohlc
def analyze_ict_from_ohlc(
    opens: list[float],
    highs: list[float],
    lows: list[float],
    closes: list[float],
    *,
    symbol: str = "",
    interval: str = "1h",
) -> dict[str, Any]:
    n = len(closes)
    if n < 40:
        return {"ok": False, "error": "داده کافی نیست (حداقل ۴۰ کندل لازم است)"}

    opens = [_f(x) for x in opens]
    highs = [_f(x) for x in highs]
    lows = [_f(x) for x in lows]
    closes = [_f(x) for x in closes]

    atr = _atr(highs, lows, closes)
    # External swings (stronger) vs internal (tighter)
    sh_ext, sl_ext = _swings(highs, lows, left=4, right=4)
    sh_int, sl_int = _swings(highs, lows, left=2, right=2)

    ext = _structure_from_swings(sh_ext, sl_ext, closes[-1], "external")
    internal = _structure_from_swings(sh_int, sl_int, closes[-1], "internal")
    fvgs = _fair_value_gaps(opens, highs, lows, closes, atr=atr)
    obs = _order_blocks(opens, highs, lows, closes, atr=atr)
    liq = _liquidity(sh_ext, sl_ext, highs, lows, closes)
    dr = _dealing_range(sh_ext, sl_ext, closes, ext.get("phase") or "neutral")
    disp = _displacement(opens, highs, lows, closes, atr)
    kz = _killzone()
    bias = _compute_bias(ext, internal, fvgs, obs, liq, dr, disp)
    scenarios = _scenarios(bias, dr, liq, ext)

    return {
        "ok": True,
        "symbol": symbol,
        "interval": interval,
        "price": closes[-1],
        "atr": atr,
        "candles": n,
        "external": ext,
        "internal": internal,
        "fvgs": fvgs,
        "order_blocks": obs,
        "liquidity": liq,
        "dealing_range": dr,
        "displacement": disp,
        "killzone": kz,
        "bias": bias,
        "scenarios": scenarios,
        "swings": {
            "ext_highs": sh_ext[-5:],
            "ext_lows": sl_ext[-5:],
        },
    }
