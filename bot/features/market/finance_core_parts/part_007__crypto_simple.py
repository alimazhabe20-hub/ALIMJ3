from typing import Any

# Auto-split part 7: _crypto_simple
async def _crypto_simple(ids: list[str]) -> dict[str, Any]:
    key = "cg_" + ",".join(sorted(ids))
    now = datetime.now().timestamp()
    if key in _cache and now - _cache_t.get(key, 0) < 60:
        return _cache[key]
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    try:
        async with pooled_async_client() as client:
            r = await request_with_retry("GET", 
                "https://api.coingecko.com/api/v3/simple/price", retries=0,
                params={
                    "ids": ",".join(ids),
                    "vs_currencies": "usd",
                    "include_24hr_change": "true",
                    "include_market_cap": "true",
                    "include_24hr_vol": "true",
                },
            )
            if r.status_code == 200:
                data = safe_json(r)
                _cache[key] = data
                _cache_t[key] = now
                return data
    except Exception as e:
        logger.error(f"coingecko simple: {e}")

    mapping = {
        "bitcoin": "btc-bitcoin", "ethereum": "eth-ethereum", "tether": "usdt-tether",
        "binancecoin": "bnb-binance-coin", "solana": "sol-solana", "ripple": "xrp-xrp",
        "the-open-network": "ton-toncoin", "dogecoin": "doge-dogecoin", "cardano": "ada-cardano",
        "tron": "trx-tron", "chainlink": "link-chainlink", "litecoin": "ltc-litecoin",
        "polkadot": "dot-polkadot", "avalanche-2": "avax-avalanche", "shiba-inu": "shib-shiba-inu",
    }
    out = {}
    try:
        async with pooled_async_client() as client:
            for cid in ids:
                pid = mapping.get(cid)
                if not pid:
                    continue
                r = await request_with_retry("GET", f"https://api.coinpaprika.com/v1/tickers/{pid}", retries=0)
                if r.status_code == 200:
                    price = safe_json(r).get("quotes", {}).get("USD", {}).get("price")
                    if price:
                        out[cid] = {"usd": float(price)}
        if out:
            _cache[key] = out
            _cache_t[key] = now
            return out
    except Exception as e:
        logger.error(f"paprika simple: {e}")
    return {}
