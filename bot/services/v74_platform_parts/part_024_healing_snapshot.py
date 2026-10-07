from typing import Any

# Auto-split part 24: healing_snapshot
def healing_snapshot() -> dict[str, Any]:
    now = time.monotonic()
    return {k: {"failures_120s": sum(1 for x in q if now-x <= 120)} for k, q in _FAILURES.items()}
