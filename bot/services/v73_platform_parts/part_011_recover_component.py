from typing import Any

# Auto-split part 11: recover_component
def recover_component(component: str) -> dict[str, Any]:
    """Safe local recovery only: clear in-memory caches and reset known clients."""
    actions: list[str] = []
    try:
        from bot.services.tool_runtime import clear_tool_cache
        clear_tool_cache()
        actions.append("tool_cache_cleared")
    except Exception:
        pass
    try:
        from bot.utils.http_client import clear_http_cache
        clear_http_cache()
        actions.append("http_cache_cleared")
    except Exception:
        pass
    _COOLDOWN_UNTIL[component] = time.monotonic() + 3
    return {"component": component, "recovered": True, "actions": actions}
