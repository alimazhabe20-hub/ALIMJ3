from typing import Any
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from bot.services.v74_platform import CACHE_TTL

# Auto-split part 18: cache_set
def cache_set(key: str, value: Any, ttl: int = CACHE_TTL) -> None:
    now = time.monotonic()
    _CACHE[key] = (now + max(1, ttl), value)
    if len(_CACHE) > CACHE_MAX:
        stale = [k for k, (exp, _) in _CACHE.items() if exp <= now]
        for k in stale[: max(1, len(stale)//2)]: _CACHE.pop(k, None)
        if len(_CACHE) > CACHE_MAX:
            for k in list(_CACHE)[: len(_CACHE)-CACHE_MAX]: _CACHE.pop(k, None)
