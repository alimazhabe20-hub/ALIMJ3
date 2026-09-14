from typing import Any

# Auto-split part 9: plugin_health
def plugin_health() -> dict[str, Any]:
    """Return a safe summary suitable for diagnostics/health endpoints."""
    items = list_plugins()
    unhealthy = [item["name"] for item in items if item["enabled"] and not item["healthy"]]
    return {"ok": not unhealthy, "total": len(items), "unhealthy": unhealthy, "plugins": items}
