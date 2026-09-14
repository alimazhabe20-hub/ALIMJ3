# Auto-split part 7: _fetch_fundamentals
async def _fetch_fundamentals(coin_id: str | None, base: str) -> dict:
    """فاندامنتال‌های سبک؛ منابع مستقل هم‌زمان خوانده می‌شوند."""
    out = {}
    retries = max(0, int(__import__('os').getenv("MARKET_HTTP_RETRIES", "0")))
    slug_map = {
        "BTC": None, "ETH": "ethereum", "SOL": "solana", "AVAX": "avalanche",
        "DOT": "polkadot", "ADA": "cardano", "TRX": "tron", "NEAR": "near",
        "MATIC": "polygon", "ARB": "arbitrum", "OP": "optimism", "SUI": "sui",
        "TON": "ton", "LINK": "chainlink",
    }
    slug = slug_map.get(base.upper())

    async def _global():
        try:
            return await request_with_retry("GET", "https://api.coingecko.com/api/v3/global", retries=retries)
        except Exception:
            return None

    async def _tvl():
        if not slug:
            return None
        try:
            return await request_with_retry("GET", f"https://api.llama.fi/tvl/{slug}", retries=retries)
        except Exception:
            return None

    async def _simple():
        if not coin_id:
            return None
        try:
            return await request_with_retry(
                "GET", "https://api.coingecko.com/api/v3/simple/price", retries=retries,
                params={
                    "ids": coin_id, "vs_currencies": "usd",
                    "include_market_cap": "true", "include_24hr_vol": "true",
                },
            )
        except Exception:
            return None

    rg, rt, rs = await asyncio.gather(_global(), _tvl(), _simple())
    if rg is not None and getattr(rg, "status_code", 0) == 200:
        g = (safe_json(rg) or {}).get("data") or {}
        out["btc_dom"] = (g.get("market_cap_percentage") or {}).get("btc")
    if rt is not None and getattr(rt, "status_code", 0) == 200:
        val = safe_json(rt)
        if isinstance(val, (int, float)) and val > 0:
            out["tvl"] = float(val)
    if rs is not None and getattr(rs, "status_code", 0) == 200 and coin_id:
        row = (safe_json(rs) or {}).get(coin_id) or {}
        out["price"] = row.get("usd")
        out["mcap"] = row.get("usd_market_cap")
        out["vol"] = row.get("usd_24h_vol")
    return out
