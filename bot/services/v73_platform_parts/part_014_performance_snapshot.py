from typing import Any

# Auto-split part 14: performance_snapshot
def performance_snapshot() -> dict[str, Any]:
    out = {}
    for name, p in _PERF.items():
        calls = max(1.0, p["calls"])
        out[name] = {
            "calls": int(p["calls"]),
            "errors": int(p["errors"]),
            "avg_ms": round(p["total_ms"] / calls, 2),
            "max_ms": round(p["max_ms"], 2),
            "slow": p["max_ms"] >= SLOW_TOOL_MS,
        }
    return out
