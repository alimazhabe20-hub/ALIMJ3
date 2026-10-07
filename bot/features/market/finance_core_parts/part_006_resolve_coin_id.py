from typing import Optional

# Auto-split part 6: resolve_coin_id
async def resolve_coin_id(symbol: str) -> Optional[str]:
    """پیدا کردن شناسه CoinGecko از نماد یا نام — پشتیبانی تقریباً همه ارزها"""
    symbol = (symbol or "").lower().strip().replace(" ", "").replace("‌", "")
    if not symbol:
        return None
    if symbol in SYMBOL_TO_ID:
        return SYMBOL_TO_ID[symbol]

    cache_key = f"resolve_{symbol}"
    now = datetime.now().timestamp()
    if cache_key in _cache and now - _cache_t.get(cache_key, 0) < 3600:
        return _cache[cache_key]

    try:
        async with pooled_async_client() as c:
            r = await request_with_retry("GET", "https://api.coingecko.com/api/v3/search", params={"query": symbol})
            if r.status_code == 200:
                coins = safe_json(r).get("coins") or []
                if coins:
                    for coin in coins:
                        if (coin.get("symbol") or "").lower() == symbol:
                            cid = coin.get("id")
                            _cache[cache_key] = cid
                            _cache_t[cache_key] = now
                            return cid
                    cid = coins[0].get("id")
                    _cache[cache_key] = cid
                    _cache_t[cache_key] = now
                    return cid
    except Exception as e:
        logger.warning(f"resolve_coin_id {symbol}: {e}")
    return None
