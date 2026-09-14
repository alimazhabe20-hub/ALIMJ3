# Auto-split part 13: record_performance
def record_performance(name: str, elapsed_ms: float, ok: bool = True) -> None:
    p = _PERF[name]
    p["calls"] += 1
    p["total_ms"] += max(0.0, elapsed_ms)
    p["max_ms"] = max(p["max_ms"], elapsed_ms)
    if not ok:
        p["errors"] += 1
