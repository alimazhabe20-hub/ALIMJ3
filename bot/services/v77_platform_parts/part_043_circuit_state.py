from typing import Any

# Auto-split part 43: circuit_state
def circuit_state(name: str) -> dict[str,Any]:
    p=_CIRCUITS.setdefault(str(name),{"failures":0,"opened_until":0.0})
    return {"open":time.monotonic()<p["opened_until"],"failures":p["failures"],"retry_at":p["opened_until"]}
