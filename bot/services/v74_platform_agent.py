"""v74_platform: agent responsibilities."""
from .v74_platform_common import *  # noqa: F401,F403
from . import v74_platform_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


class AgentStep:
    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)
    reason: str = ""

def _agent_intents(goal: str, available: set[str]) -> list[AgentStep]:
    q = (goal or "").lower()
    patterns: list[tuple[str, str, str, dict[str, Any], int]] = [
        (r"هوا|آب\s*و\s*هوا|دما|باران|weather", "get_weather", "weather", {}, 4),
        (r"آلودگی|کیفیت\s*هوا|aqi|air", "get_air_quality", "air_quality", {}, 4),
        (r"قیمت|بازار|کریپتو|بیت.?کوین|طلا|دلار|ارز|market|price", "get_market_prices", "market", {}, 5),
        (r"تقویم\s*اقتصادی|economic\s*calendar|اخبار\s*اقتصادی", "get_economic_calendar", "calendar", {}, 5),
        (r"مستندات|راهنما|قابلیت.*ربات|knowledge|documentation", "search_knowledge_base", "knowledge", {"query": goal}, 4),
        (r"اینترنت|وب|جستجو|خبر|اخبار|latest|news|search", "hybrid_retrieve", "web", {"query": goal, "include_web": True}, 5),
        (r"خرید|بخر|فروشگاه|shopping|قیمت.*محصول", "search_shopping", "shopping", {"query": goal, "source": "all", "max_results": 8}, 4),
    ]
    found: list[tuple[int, AgentStep]] = []
    for pattern, tool, reason, args, score in patterns:
        if tool in available and re.search(pattern, q, re.I):
            found.append((score, AgentStep(tool, dict(args), reason)))
    found.sort(key=lambda x: (-x[0], x[1].tool))
    return [x[1] for x in found[:MAX_AGENT_STEPS]]

def _should_stop(goal: str, step: AgentStep, result: str) -> bool:
    low = (goal + " " + result).lower()
    if any(x in low for x in ("فقط", "تنها", "just", "only")) and step.reason in {"market", "weather", "air_quality", "calendar"}:
        return True
    return bool(result) and not str(result).startswith(("خطا", "ابزار ناشناخته", "ابزار مسدود", "زمان اجرای")) and step.reason in {"weather", "air_quality"}

async def run_agent_2(goal: str, *, user_id: int = 0) -> str:
    goal = (goal or "").strip()[:6000]
    if not goal:
        return "هدف خالی است."
    injection = detect_prompt_injection(goal)
    from bot.services.tool_runtime import execute_tool, get_registered_tool_names
    available = get_registered_tool_names()
    plan = _agent_intents(goal, available)
    if not plan:
        return "برای این درخواست ابزار مطمئنی لازم نیست؛ پاسخ مستقیم مناسب‌تر است."
    started = time.monotonic()
    trace: list[dict[str, Any]] = []
    used: set[str] = set()
    calls = repairs = 0
    for idx, step in enumerate(plan, 1):
        if calls >= MAX_AGENT_CALLS or (time.monotonic() - started) * 1000 >= AGENT_BUDGET_MS or step.tool in used:
            break
        allowed, reason = tool_allowed(step.tool, source="agent")
        if not allowed:
            trace.append({"step": idx, "tool": step.tool, "ok": False, "blocked": reason})
            continue
        used.add(step.tool); calls += 1
        t0 = time.monotonic()
        try:
            result = await execute_tool(step.tool, step.arguments, user_id=user_id, source="agent")
            ok = not str(result).startswith(("خطا در اجرای", "زمان اجرای", "ابزار ناشناخته", "ابزار مسدود", "ابزار موقتاً"))
            trace.append({"step": idx, "tool": step.tool, "reason": step.reason, "ok": ok,
                          "elapsed_ms": round((time.monotonic()-t0)*1000, 1), "result": redact_secrets(result)[:2500]})
            if not ok and repairs < MAX_AGENT_REPAIRS and "hybrid_retrieve" in available and "hybrid_retrieve" not in used:
                repairs += 1; calls += 1; used.add("hybrid_retrieve")
                repaired = await execute_tool("hybrid_retrieve", {"query": goal, "include_web": True}, user_id=user_id, source="agent_repair")
                trace.append({"step": idx, "tool": "hybrid_retrieve", "repair": True,
                              "ok": not str(repaired).startswith("خطا"), "result": redact_secrets(repaired)[:2500]})
            if ok and _should_stop(goal, step, str(result)):
                break
        except Exception:
            logger.warning("V74 agent step failed", exc_info=True)
            trace.append({"step": idx, "tool": step.tool, "ok": False, "error": "internal_failure"})
            if repairs < MAX_AGENT_REPAIRS:
                repairs += 1
    return json.dumps({"ok": bool(trace), "goal": goal[:500], "steps": trace, "calls": calls,
                       "repairs": repairs, "budget_ms": AGENT_BUDGET_MS,
                       "prompt_injection": injection}, ensure_ascii=False)[:12000]

def note_tool_failure(name: str) -> bool:
    now = time.monotonic()
    q = _TOOL_FAILURES[name]
    q.append(now)
    recent = sum(1 for x in q if now - x <= 120)
    if recent >= max(3, int(os.getenv("V74_TOOL_FAILURE_THRESHOLD", "4"))):
        _TOOL_DISABLED_UNTIL[name] = now + max(10, int(os.getenv("V74_TOOL_COOLDOWN", "45")))
        return True
    return False

def recover_tool(name: str) -> dict[str, Any]:
    _TOOL_DISABLED_UNTIL[name] = time.monotonic() + 3
    try:
        from bot.services.tool_runtime import clear_tool_cache
        clear_tool_cache()
    except Exception:
        pass
    return {"tool": name, "recovered": True, "action": "cache_clear_and_short_cooldown"}
