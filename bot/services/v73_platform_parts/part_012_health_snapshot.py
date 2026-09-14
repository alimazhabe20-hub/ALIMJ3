from typing import Any

# Auto-split part 12: health_snapshot
def health_snapshot() -> dict[str, Any]:
    now = time.monotonic()
    return {
        name: {
            "failures_120s": sum(1 for x in q if now - x <= 120),
            "cooldown_remaining": round(max(0.0, _COOLDOWN_UNTIL.get(name, 0.0) - now), 1),
        }
        for name, q in _FAILURES.items()
    }
