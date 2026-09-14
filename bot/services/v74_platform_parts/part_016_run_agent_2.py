# Auto-split part 16: run_agent_2
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
