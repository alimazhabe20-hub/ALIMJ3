from typing import Iterable
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from bot.services.v75_platform import AgentTask

# Auto-split part 7: plan_agent
def plan_agent(goal: str, available_tools: Iterable[str] = ()) -> AgentTask:
    goal = redact(goal, 6000).strip()
    available = set(available_tools)
    if not goal:
        return AgentTask(uuid.uuid4().hex, "", [], "rejected")
    scan = security_scan(goal)
    if scan["risk"] == "high":
        return AgentTask(uuid.uuid4().hex, goal, [], "security_blocked")
    patterns = [
        (r"هوا|weather", "get_weather", {"query": goal}),
        (r"بازار|قیمت|کریپتو|بیت.?کوین|طلا|ارز|market|price", "get_market_prices", {"query": goal}),
        (r"تقویم|خبر اقتصادی|economic calendar", "get_economic_calendar", {"query": goal}),
        (r"خبر|اخبار|news|latest|وب|جستجو|search", "hybrid_retrieve", {"query": goal, "include_web": True}),
        (r"خرید|محصول|shopping", "search_shopping", {"query": goal, "source": "all", "max_results": 8}),
        (r"مستند|دانش|راهنما|knowledge", "search_knowledge_base", {"query": goal}),
    ]
    steps = []
    for pattern, tool, args in patterns:
        if tool in available and re.search(pattern, goal, re.I):
            steps.append({"tool": tool, "arguments": args, "reason": "intent_match"})
    # Multi-agent style specialist stages: research -> domain -> reviewer.
    if len(steps) > MAX_AGENT_STEPS:
        steps = steps[:MAX_AGENT_STEPS]
    return AgentTask(uuid.uuid4().hex, goal, steps, "planned" if steps else "direct_answer")
