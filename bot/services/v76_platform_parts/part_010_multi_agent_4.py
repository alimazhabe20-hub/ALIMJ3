from typing import Any

# Auto-split part 10: multi_agent_4
async def multi_agent_4(goal: str, *, user_id: int = 0) -> dict[str, Any]:
    r=await run_agent_4(goal,user_id=user_id)
    specialists=[{"role":"researcher" if "search" in x["tool"] else "domain","tool":x["tool"],"ok":x["ok"]} for x in r["steps"]]
    return {**r,"specialists":specialists,"review":all(x["verified"] for x in r["steps"]) if r["steps"] else False}
