"""v75_platform: agent responsibilities."""
from .v75_platform_common import *  # noqa: F401,F403
from . import v75_platform_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


class AgentTask:
    id: str
    goal: str
    steps: list[dict[str, Any]]
    status: str = "planned"

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

async def run_agent_3(goal: str, *, user_id: int = 0) -> dict[str, Any]:
    from bot.services.tool_runtime import execute_tool, get_registered_tool_names
    task = plan_agent(goal, get_registered_tool_names())
    if task.status != "planned":
        return {"ok": task.status == "direct_answer", "task_id": task.id, "status": task.status, "steps": []}
    started = time.monotonic(); results = []; seen = set()
    for index, step in enumerate(task.steps[:MAX_AGENT_STEPS], 1):
        if len(results) >= MAX_AGENT_CALLS or (time.monotonic() - started) * 1000 >= MAX_AGENT_MS:
            break
        tool = step["tool"]
        if tool in seen:
            continue
        seen.add(tool)
        t0 = time.monotonic()
        result = await execute_tool(tool, step.get("arguments", {}), user_id=user_id, source="agent")
        ok = not str(result).startswith(("خطا در اجرای", "زمان اجرای", "ابزار ناشناخته", "ابزار مسدود"))
        results.append({"step": index, "tool": tool, "ok": ok, "latency_ms": round((time.monotonic()-t0)*1000, 1), "result": redact(result, 2500)})
        if not ok:
            # One bounded reviewer/repair path; never recursive.
            break
    task.status = "completed" if results and all(x["ok"] for x in results) else "partial" if results else "failed"
    return {"ok": task.status in {"completed", "partial"}, "task_id": task.id, "status": task.status,
            "goal": task.goal, "steps": results, "elapsed_ms": round((time.monotonic()-started)*1000, 1)}

async def run_multi_agent(goal: str, *, user_id: int = 0) -> dict[str, Any]:
    """Bounded specialist orchestration using existing tools, not independent LLM loops."""
    result = await run_agent_3(goal, user_id=user_id)
    specialists = []
    for item in result.get("steps", []):
        specialists.append({"specialist": _specialist_for(item["tool"]), "tool": item["tool"], "ok": item["ok"]})
    return {**result, "specialists": specialists, "reviewed": bool(result.get("steps"))}

def _specialist_for(tool: str) -> str:
    if "market" in tool: return "finance"
    if "calendar" in tool: return "economics"
    if "search" in tool or "retrieve" in tool: return "research"
    if "weather" in tool: return "utility"
    return "general"
