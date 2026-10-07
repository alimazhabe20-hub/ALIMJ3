"""v77_platform: agent responsibilities."""
from .v77_platform_common import *  # noqa: F401,F403
from . import v77_platform_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


class AgentStep:
    id: str
    tool: str
    arguments: dict[str, Any]
    depends_on: list[str]
    verify: bool = True
    retries: int = 1

class AgentPlan:
    id: str
    goal: str
    steps: list[AgentStep]
    budget_ms: int = 90000
    max_calls: int = MAX_CALLS

def advanced_intent(text: str) -> dict[str, Any]:
    s = str(text or "").strip().lower()
    rules = [
        ("market", r"بازار|قیمت|کریپتو|بیت.?کوین|اتریوم|طلا|ارز|btc|eth|gold|crypto"),
        ("news", r"خبر|اخبار|نیوز|news|latest|خبر جدید"),
        ("calendar", r"تقویم|تقویم اقتصادی|economic calendar|cpi|ppi|nfp|fomc|نرخ بهره"),
        ("web", r"جستجو|وب|منبع|سرچ|search|research"),
        ("download", r"دانلود|download|لینک فایل|فایل دانلود"),
        ("document", r"pdf|word|excel|سند|فایل|متن فایل|جدول"),
        ("report", r"گزارش|report|xlsx|csv|pdf گزارش"),
        ("alert", r"هشدار|آلارم|alert|اعلان قیمت"),
        ("backup", r"بکاپ|پشتیبان|backup|restore|بازیابی"),
        ("system", r"سلامت|وضعیت سیستم|health|status|diagnostic|عیب"),
        ("code", r"کد|برنامه|python|code|bug|باگ"),
    ]
    candidates = [name for name, pat in rules if re.search(pat, s, re.I)]
    return {"primary": candidates[0] if candidates else "general", "candidates": candidates, "needs_tool": bool(candidates), "confidence": min(1.0, 0.35 + 0.15 * len(candidates))}

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

def verify_result(result: Any, *, expected: str = "") -> dict[str, Any]:
    text = redact(result, 6000).strip()
    failed = not text or text.startswith(("خطا", "Error", "ابزار ناشناخته", "Tool blocked", "زمان اجرای"))
    return {"ok": not failed, "nonempty": bool(text), "expected_match": bool(expected and expected.lower() in text.lower()), "safe": not bool(_SECRET.search(text)), "preview": text[:1000]}

async def run_agent_5(goal: str, *, user_id: int = 0) -> dict[str, Any]:
    from bot.services.tool_runtime import execute_tool, get_registered_tool_names
    plan = build_agent_plan(goal, get_registered_tool_names())
    if not plan.steps:
        return {"ok": bool(plan.goal), "status": "direct_or_blocked", "plan": asdict(plan), "steps": []}
    started = time.monotonic(); results=[]; completed=set(); calls=0
    for step in plan.steps:
        if calls >= plan.max_calls or (time.monotonic()-started)*1000 >= plan.budget_ms:
            break
        if any(dep not in completed for dep in step.depends_on):
            continue
        last = None
        for attempt in range(step.retries + 1):
            if calls >= plan.max_calls: break
            calls += 1; t=time.monotonic()
            try:
                result = await asyncio.wait_for(execute_tool(step.tool, step.arguments, user_id=user_id, source="agent5"), timeout=20)
                check = verify_result(result)
                last = {"step_id": step.id, "tool": step.tool, "attempt": attempt+1, "ok": check["ok"], "verified": check, "latency_ms": round((time.monotonic()-t)*1000,1), "result": redact(result,3000)}
                if check["ok"]: completed.add(step.id); break
            except Exception:
                last = {"step_id": step.id, "tool": step.tool, "attempt": attempt+1, "ok": False, "verified": {"ok":False}, "latency_ms": round((time.monotonic()-t)*1000,1), "result": "tool execution failed"}
        if last: results.append(last)
        if last and not last["ok"]: break
    status="completed" if results and all(x["ok"] for x in results) else "partial" if results else "failed"
    return {"ok": status in {"completed","partial"}, "status":status, "plan":asdict(plan), "steps":results, "calls":calls, "elapsed_ms":round((time.monotonic()-started)*1000,1)}

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
