from typing import Any

# Auto-split part 39: runtime_snapshot
def runtime_snapshot() -> dict[str, Any]:
    return {"uptime_s":round(max(0,time.time()-_RUNTIME["started_at"]),1), "readiness":dict(_RUNTIME["readiness"]),
            "last_errors":list(_RUNTIME["last_errors"])}
