from typing import Iterable
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from bot.services.v77_platform import AgentPlan

# Auto-split part 10: build_agent_plan
def build_agent_plan(goal: str, tools: Iterable[str] = ()) -> AgentPlan:
    goal = redact(goal, 8000).strip()
    if not goal or security_scan(goal)["risk"] == "high":
        return AgentPlan(uuid.uuid4().hex, goal, [], 30000, 2)
    available = set(tools)
    mapping = {
        "market": "get_market_prices", "news": "hybrid_retrieve", "calendar": "get_economic_calendar",
        "web": "hybrid_retrieve", "download": "download_file", "document": "search_knowledge_base",
        "report": "generate_report", "system": "v77_system_status",
    }
    steps: list[AgentStep] = []
    for kind in advanced_intent(goal)["candidates"]:
        tool = mapping.get(kind)
        if tool and tool in available and tool not in {x.tool for x in steps}:
            deps = [steps[-1].id] if kind in {"report", "system"} and steps else []
            steps.append(AgentStep(uuid.uuid4().hex[:10], tool, {"query": goal}, deps, True, 1))
    return AgentPlan(uuid.uuid4().hex, goal, steps[:MAX_STEPS])
