from typing import Any

# Auto-split part 56: self_healing_snapshot
def self_healing_snapshot() -> dict[str,Any]:
    return {"circuits":{k:circuit_state(k) for k in _CIRCUITS},"failures":{k:len(v) for k,v in _FAILURES.items() if v},"policy":"bounded_retry_then_circuit"}
