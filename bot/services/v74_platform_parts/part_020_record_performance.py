# Auto-split part 20: record_performance
def record_performance(component: str, elapsed_ms: float, ok: bool = True) -> None:
    p = _PERF[component]
    p["calls"] += 1; p["total_ms"] += max(0.0, elapsed_ms); p["max_ms"] = max(p["max_ms"], elapsed_ms)
    if not ok: p["errors"] += 1
    if elapsed_ms >= float(os.getenv("V74_SLOW_MS", "3000")): _SLOW[component] += 1
