from typing import Any

# Auto-split part 33: cache_get
def cache_get(key: str) -> Any:
    k=str(key); x=_CACHE.get(k)
    if not x:return None
    if x[0]<=time.monotonic():_CACHE.pop(k,None);return None
    _CACHE.move_to_end(k);return x[1]
