"""finance_core: pricing responsibilities."""
from .finance_core_common import *  # noqa: F401,F403
from . import finance_core_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


async def _get_usd_rial() -> int | None:
    return await _tgju_price("price_dollar_rl")

def pn(n: Any) -> str:
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))

def _parse_price(raw: Any) -> int | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return int(raw)
    text = str(raw).replace(",", "").replace("٬", "").replace(" ", "").strip()
    if not text:
        return None
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None

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
