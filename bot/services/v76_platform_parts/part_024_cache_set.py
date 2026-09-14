from typing import Any

# Auto-split part 24: cache_set
def cache_set(key: str, value: Any, ttl: float=30) -> None:
    if len(_CACHE)>=MAX_CACHE:
        for k in list(_CACHE)[:max(1,len(_CACHE)-MAX_CACHE+1)]: _CACHE.pop(k,None)
    _CACHE[str(key)]=(time.monotonic()+max(1,float(ttl)),value)
