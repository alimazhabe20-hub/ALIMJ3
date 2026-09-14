from typing import Any

# Auto-split part 13: unified_tool_execute
async def unified_tool_execute(tool: str, arguments: dict[str, Any] | None = None, *, user_id: int = 0) -> dict[str, Any]:
    """Single safe bridge to the existing tool runtime; never executes code strings."""
    from bot.services.tool_runtime import execute_tool, get_registered_tool_names
    if tool not in set(get_registered_tool_names()):
        return {"ok":False,"error":"unknown_tool"}
    if security_scan(json.dumps(arguments or {}, ensure_ascii=False))["risk"] == "high":
        return {"ok":False,"error":"blocked_input"}
    try:
        out = await asyncio.wait_for(execute_tool(tool, arguments or {}, user_id=user_id, source="v77"), timeout=30)
        return {"ok":True,"result":redact(out,6000)}
    except Exception:
        return {"ok":False,"error":"tool_execution_failed"}
