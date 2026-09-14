from typing import Any

# Auto-split part 23: cache_get
def cache_get(key: str) -> Any:
    x=_CACHE.get(str(key));
    if not x: return None
    if x[0]<=time.monotonic(): _CACHE.pop(str(key),None); return None
    return x[1]
