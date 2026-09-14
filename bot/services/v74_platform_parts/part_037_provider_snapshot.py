from typing import Any

# Auto-split part 37: provider_snapshot
def provider_snapshot() -> dict[str, Any]:
    return {k:{"calls":int(v["calls"]),"errors":int(v["errors"]),"avg_ms":round(v["total_ms"]/max(1,v["calls"]),2),
               "available":provider_available(k)} for k,v in sorted(_PROVIDER.items())}
