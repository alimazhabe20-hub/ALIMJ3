from typing import Any

# Auto-split part 21: market_intelligence
async def market_intelligence(symbol: str, timeframes: tuple[str, ...] = ("1h", "4h", "1d")) -> dict[str, Any]:
    from bot.features.market.finance import _fetch_klines_interval
    from bot.features.market.finance_ta import _compute_ta
    from bot.features.market.finance_core import resolve_coin_id, _crypto_simple
    normalized = (symbol or "").strip().lower()
    cid = await resolve_coin_id(normalized)
    price = None
    if cid:
        data = await _crypto_simple([cid]); row = data.get(cid) or {}; price = row.get("usd")
    result = {"symbol": normalized, "coin_id": cid, "price_usd": price, "timeframes": {}, "confluence": 0}
    scores = []
    for tf in timeframes:
        pair = normalized.upper().replace("-", "") + "USDT"
        limit = 200
        try:
            interval = {"1h": "1h", "4h": "4h", "1d": "1d"}.get(tf, "1h")
            rows = await _fetch_klines_interval(pair, interval, limit)
            closes = [float(r[4]) for r in rows]; highs = [float(r[2]) for r in rows]; lows = [float(r[3]) for r in rows]; vols = [float(r[5]) for r in rows]
            ta = _compute_ta(closes, highs, lows, vols) if closes else {}
            result["timeframes"][tf] = ta
            scores.append(1 if ta.get("trend") == "صعودی" else -1 if ta.get("trend") == "نزولی" else 0)
        except Exception as exc:
            logger.debug("market intelligence %s %s: %s", normalized, tf, type(exc).__name__)
            result["timeframes"][tf] = {"error": "unavailable"}
    confluence = sum(scores)
    result["confluence"] = confluence
    result["bias"] = "bullish" if confluence >= 2 else "bearish" if confluence <= -2 else "mixed"
    result["risk"] = "high" if abs(confluence) <= 1 else "medium"
    return result
