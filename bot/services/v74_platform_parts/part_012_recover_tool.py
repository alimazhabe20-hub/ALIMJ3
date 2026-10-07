from typing import Any

# Auto-split part 12: recover_tool
def recover_tool(name: str) -> dict[str, Any]:
    _TOOL_DISABLED_UNTIL[name] = time.monotonic() + 3
    try:
        from bot.services.tool_runtime import clear_tool_cache
        clear_tool_cache()
    except Exception:
        pass
    return {"tool": name, "recovered": True, "action": "cache_clear_and_short_cooldown"}
