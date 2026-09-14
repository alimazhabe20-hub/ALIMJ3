# Auto-split part 5: _tgju_price
async def _tgju_price(slug: str) -> int | None:
    key = f"tgju_{slug}"
    now = datetime.now().timestamp()
    if key in _cache and now - _cache_t.get(key, 0) < _BULK_TTL:
        return _cache[key]

    bulk = await _fetch_tgju_bulk()
    item = bulk.get(slug)
    if isinstance(item, dict):
        val = _parse_price(item.get("p"))
    else:
        val = _parse_price(item)

    if val is not None:
        _cache[key] = val
        _cache_t[key] = now
        return val

    try:
        url = f"https://www.tgju.org/profile/{slug}"
        async with pooled_async_client() as c:
            r = await request_with_retry("GET", url, retries=0)
            r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        tag = soup.find(attrs={"data-col": "info.last_trade.PDrCotVal"})
        if tag:
            val = _parse_price(tag.get_text(strip=True))
            if val:
                _cache[key] = val
                _cache_t[key] = now
                return val
    except Exception as e:
        logger.error(f"tgju fallback {slug}: {e}")
    return None
