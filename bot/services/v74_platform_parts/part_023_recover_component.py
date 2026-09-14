from typing import Any

# Auto-split part 23: recover_component
def recover_component(component: str) -> dict[str, Any]:
    actions: list[str] = []
    try:
        clear_performance_cache(); actions.append("performance_cache_cleared")
    except Exception: pass
    try:
        from bot.services.tool_runtime import clear_tool_cache
        clear_tool_cache(); actions.append("tool_cache_cleared")
    except Exception: pass
    _RECOVERY_LOG.append({"component": component, "action": "recovered", "at": time.time()})
    return {"component": component, "recovered": True, "actions": actions}
