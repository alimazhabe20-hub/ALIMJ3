from typing import Any

# Auto-split part 9: _top_from_paprika
async def _top_from_paprika(limit: int = 20) -> list[dict[str, Any]]:
    try:
        async with pooled_async_client() as client:
            r = await request_with_retry("GET", "https://api.coinpaprika.com/v1/tickers", retries=0)
            if r.status_code != 200:
                return []
            data = safe_json(r) or []
            data = sorted(data, key=lambda x: x.get("rank") or 9999)[:limit]
            out = []
            for row in data:
                q = (row.get("quotes") or {}).get("USD") or {}
                out.append({
                    "symbol": (row.get("symbol") or "").upper(),
                    "price": float(q.get("price") or 0),
                    "chg": float(q.get("percent_change_24h") or 0),
                })
            return out
    except Exception as e:
        logger.error(f"paprika top: {e}")
        return []
