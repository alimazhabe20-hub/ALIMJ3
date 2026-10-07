"""v74_platform: performance responsibilities."""
from .v74_platform_common import *  # noqa: F401,F403
from . import v74_platform_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def cache_get(key: str) -> Any | None:
    item = _CACHE.get(key)
    if not item:
        return None
    if item[0] <= time.monotonic():
        _CACHE.pop(key, None); return None
    return item[1]

def cache_set(key: str, value: Any, ttl: int = CACHE_TTL) -> None:
    now = time.monotonic()
    _CACHE[key] = (now + max(1, ttl), value)
    if len(_CACHE) > CACHE_MAX:
        stale = [k for k, (exp, _) in _CACHE.items() if exp <= now]
        for k in stale[: max(1, len(stale)//2)]: _CACHE.pop(k, None)
        if len(_CACHE) > CACHE_MAX:
            for k in list(_CACHE)[: len(_CACHE)-CACHE_MAX]: _CACHE.pop(k, None)

def clear_performance_cache() -> None:
    _CACHE.clear()

def record_performance(component: str, elapsed_ms: float, ok: bool = True) -> None:
    p = _PERF[component]
    p["calls"] += 1; p["total_ms"] += max(0.0, elapsed_ms); p["max_ms"] = max(p["max_ms"], elapsed_ms)
    if not ok: p["errors"] += 1
    if elapsed_ms >= float(os.getenv("V74_SLOW_MS", "3000")): _SLOW[component] += 1

def performance_snapshot() -> dict[str, Any]:
    return {k: {"calls": int(v["calls"]), "errors": int(v["errors"]),
                 "avg_ms": round(v["total_ms"]/max(1, v["calls"]), 2),
                 "max_ms": round(v["max_ms"], 2), "slow_count": _SLOW[k]}
            for k, v in sorted(_PERF.items())}

def note_failure(component: str, error: str = "") -> bool:
    now = time.monotonic(); q = _FAILURES[component]; q.append(now)
    threshold = max(3, int(os.getenv("V74_FAILURE_THRESHOLD", "4")))
    tripped = sum(1 for x in q if now-x <= 120) >= threshold
    if tripped:
        _RECOVERY_LOG.append({"component": component, "action": "cooldown", "error": redact_secrets(error)[:500], "at": time.time()})
    return tripped

def recover_component(component: str) -> dict[str, Any]:
    actions: list[str] = []
    try:
        clear_performance_cache(); actions.append("performance_cache_cleared")
    except Exception: pass
    try:
        from bot.services.tool_runtime import clear_tool_cache
        clear_tool_cache(); actions.append("tool_cache_cleared")
    except Exception: pass
    _RECOVERY_LOG.append({"component": component, "action": "recovered", "at": time.time()})
    return {"component": component, "recovered": True, "actions": actions}

def healing_snapshot() -> dict[str, Any]:
    now = time.monotonic()
    return {k: {"failures_120s": sum(1 for x in q if now-x <= 120)} for k, q in _FAILURES.items()}
