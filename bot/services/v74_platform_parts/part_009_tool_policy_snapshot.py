from typing import Any

# Auto-split part 9: tool_policy_snapshot
def tool_policy_snapshot() -> dict[str, Any]:
    now = time.monotonic()
    return {
        name: {
            "version": p.version, "risk": p.risk, "network": p.network,
            "timeout": p.timeout, "retries": p.retries, "cache_ttl": p.cache_ttl,
            "dependencies": list(p.dependencies), "enabled": p.enabled,
            "cooldown": round(max(0.0, _TOOL_DISABLED_UNTIL.get(name, 0) - now), 1),
        }
        for name, p in sorted(_TOOL_POLICIES.items())
    }
