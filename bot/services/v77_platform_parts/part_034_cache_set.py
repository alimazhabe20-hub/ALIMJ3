from typing import Any

# Auto-split part 34: cache_set
def cache_set(key: str, value: Any, ttl: float=30) -> None:
    k=str(key);_CACHE[k]=(time.monotonic()+max(.5,float(ttl)),value);_CACHE.move_to_end(k)
    while len(_CACHE)>CACHE_MAX:_CACHE.popitem(last=False)
