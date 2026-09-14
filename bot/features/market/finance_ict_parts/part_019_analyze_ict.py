# Auto-split part 19: analyze_ict
async def analyze_ict(symbol: str, interval: str = "1h", limit: int = 250) -> str:
    """Fetch OHLCV and return professional Persian ICT report."""
    from bot.features.market.finance_ta import _fetch_klines_for_ta
    from bot.features.market import finance as fin

    raw = (symbol or "btc").lower().strip()
    for junk in (
        "تحلیل", "ict", "آی‌سی‌تی", "اسیتی", "usdt", "تحلیل ict",
        "به روش", "روش",
    ):
        raw = raw.replace(junk, "")
    raw = raw.strip() or "btc"
    parts = raw.split()
    sym = parts[0]
    if len(parts) > 1 and parts[1] in ("15m", "15", "1h", "4h", "1d", "h1", "h4", "daily"):
        interval = parts[1]

    iv = {
        "15": "15m", "15m": "15m",
        "1h": "1h", "h1": "1h", "60m": "1h",
        "4h": "4h", "h4": "4h",
        "1d": "1d", "1day": "1d", "daily": "1d",
    }.get((interval or "1h").lower(), "1h")

    pair = f"{sym.upper()}USDT"
    if sym in ("gold", "xau", "xauusd"):
        pair = "PAXGUSDT"
        sym = "xau"

    klines: list = []
    try:
        if hasattr(fin, "_fetch_klines_interval"):
            klines = await fin._fetch_klines_interval(pair, iv, int(limit))
        if not klines:
            klines = await _fetch_klines_for_ta(pair, limit=limit)
            iv = "1h"
    except Exception as e:
        logger.warning("ICT klines failed: %s", e)

    if not klines or len(klines) < 40:
        return (
            f"❌ داده کندل کافی برای {sym.upper()} یافت نشد.\n"
            "مثال: btc | eth 4h | sol 1h | btc 15m"
        )

    opens = [_f(k[1]) for k in klines]
    highs = [_f(k[2]) for k in klines]
    lows = [_f(k[3]) for k in klines]
    closes = [_f(k[4]) for k in klines]

    data = analyze_ict_from_ohlc(
        opens, highs, lows, closes, symbol=sym, interval=iv
    )
    return format_ict_report(data)
