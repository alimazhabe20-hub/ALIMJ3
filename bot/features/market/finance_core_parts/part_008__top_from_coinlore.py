from typing import Any

# Auto-split part 8: _top_from_coinlore
async def _top_from_coinlore(limit: int = 20) -> list[dict[str, Any]]:
    try:
        async with pooled_async_client() as client:
            r = await request_with_retry("GET", f"https://api.coinlore.net/api/tickers/?start=0&limit={limit}", retries=0)
            if r.status_code != 200:
                return []
            data = (safe_json(r) or {}).get("data") or []
            out = []
            for row in data:
                out.append({
                    "symbol": (row.get("symbol") or "").upper(),
                    "price": float(row.get("price_usd") or 0),
                    "chg": float(row.get("percent_change_24h") or 0),
                })
            return out
    except Exception as e:
        logger.error(f"coinlore: {e}")
        return []
