from typing import Any

# Auto-split part 21: performance_snapshot
def performance_snapshot() -> dict[str, Any]:
    return {k: {"calls": int(v["calls"]), "errors": int(v["errors"]),
                 "avg_ms": round(v["total_ms"]/max(1, v["calls"]), 2),
                 "max_ms": round(v["max_ms"], 2), "slow_count": _SLOW[k]}
            for k, v in sorted(_PERF.items())}
