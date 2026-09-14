# Auto-split part 1: _fetch_klines_for_ta
async def _fetch_klines_for_ta(pair: str, limit: int = 200) -> list:
    """OHLCV از Binance Vision برای تحلیل تکنیکال"""
    try:
        async with pooled_async_client() as c:
            r = await request_with_retry("GET", 
                "https://data-api.binance.vision/api/v3/klines",
                params={"symbol": pair, "interval": "1h", "limit": limit},
            )
            if r.status_code == 200:
                return safe_json(r, []) or []
            # OKX fallback
            okx = pair.replace("USDT", "-USDT")
            r2 = await request_with_retry("GET", 
                "https://www.okx.com/api/v5/market/candles",
                params={"instId": okx, "bar": "1H", "limit": str(min(limit, 300))},
            )
            if r2.status_code == 200:
                data = (safe_json(r2, {}) or {}).get("data") or []
                # OKX newest first → reverse; map to binance-like
                out = []
                for row in reversed(data):
                    out.append([int(row[0]), row[1], row[2], row[3], row[4], row[5]])
                return out
    except Exception as e:
        logger.warning(f"klines ta: {e}")
    return []
