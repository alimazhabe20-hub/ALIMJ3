# Auto-split part 10: alert_flags
def alert_flags(current, support=None, resistance=None, ta=None, binance=None, market=None) -> list:
    ta, binance, market = ta or {}, binance or {}, market or {}
    flags=[]
    if current is not None and resistance and current > resistance: flags.append("breakout_above_resistance")
    if current is not None and support and current < support: flags.append("breakdown_below_support")
    if float(ta.get("vol_ratio") or 0) >= 1.8: flags.append("volume_spike")
    fr=binance.get("funding_rate")
    if fr is not None and abs(float(fr)) >= .08: flags.append("funding_extreme")
    liq=float(binance.get("liquidations_total") or 0)
    if liq > 0: flags.append("liquidation_activity")
    if bool((market.get("news") or {}).get("count")) and (market.get("news") or {}).get("label") in ("مثبت","منفی"):
        flags.append("news_sentiment_shift")
    return flags
