from typing import Any

# Auto-split part 4: _fetch_tgju_bulk
async def _fetch_tgju_bulk() -> dict[str, Any]:
    now = datetime.now().timestamp()
    if _BULK_CACHE_KEY in _cache and now - _cache_t.get(_BULK_CACHE_KEY, 0) < _BULK_TTL:
        return _cache[_BULK_CACHE_KEY]

    current = {}
    async with pooled_async_client() as client:
        for url in _AJAX_URLS:
            try:
                r = await request_with_retry("GET", url, retries=0)
                if r.status_code == 200:
                    data = safe_json(r) or {}
                    current = data.get("current") or {}
                    if current:
                        break
            except (httpx.HTTPError, OSError, RuntimeError) as exc:
                logger.warning("tgju ajax %s: %s", url, exc)

    if current:
        _cache[_BULK_CACHE_KEY] = current
        _cache_t[_BULK_CACHE_KEY] = now
        return current
    # stale-while-error: market values are better than an avoidable outage.
    return _cache.get(_BULK_CACHE_KEY, {})
