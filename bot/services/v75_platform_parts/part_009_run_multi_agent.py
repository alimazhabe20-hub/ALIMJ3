from typing import Any

# Auto-split part 9: run_multi_agent
async def run_multi_agent(goal: str, *, user_id: int = 0) -> dict[str, Any]:
    """Bounded specialist orchestration using existing tools, not independent LLM loops."""
    result = await run_agent_3(goal, user_id=user_id)
    specialists = []
    for item in result.get("steps", []):
        specialists.append({"specialist": _specialist_for(item["tool"]), "tool": item["tool"], "ok": item["ok"]})
    return {**result, "specialists": specialists, "reviewed": bool(result.get("steps"))}
