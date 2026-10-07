from typing import Any

# Auto-split part 17: cache_get
def cache_get(key: str) -> Any | None:
    item = _CACHE.get(key)
    if not item:
        return None
    if item[0] <= time.monotonic():
        _CACHE.pop(key, None); return None
    return item[1]
