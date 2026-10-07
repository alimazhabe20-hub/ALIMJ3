# Auto-split part 8: run_production_agent
async def run_production_agent(goal: str, *, user_id: int = 0) -> str:
    """Bounded agent with planning, policy checks, repair, trace and safe output."""
    goal = (goal or "").strip()
    if not goal:
        return "هدف خالی است."
    from bot.services.tool_runtime import execute_tool, get_registered_tool_names

    run = AgentRun(goal, user_id)
    available = get_registered_tool_names()
    plan = _intent_candidates(goal, available)
    if not plan:
        return "برای این درخواست برنامه ابزارمحور مطمئنی پیدا نشد؛ پاسخ مستقیم AI مناسب‌تر است."

    for idx, step in enumerate(plan, 1):
        tool = step["tool"]
        args = sanitize_tool_arguments(step.get("arguments") or {})
        if not run.can_call(tool):
            break
        run.calls += 1
        run.used.add(tool)
        started = time.monotonic()
        try:
            value = await execute_tool(tool, args, user_id=user_id, source="agent")
            failed = isinstance(value, str) and value.startswith(("خطا در اجرای", "زمان اجرای", "ابزار ناشناخته", "ابزار مسدود"))
            run.record(step=idx, tool=tool, ok=not failed, result=redact_secrets(value)[:3000])
            if failed and run.repairs < MAX_AGENT_REPAIRS:
                run.repairs += 1
                fallback = "hybrid_retrieve" if "hybrid_retrieve" in available and tool != "hybrid_retrieve" else None
                if fallback and run.can_call(fallback):
                    run.calls += 1
                    run.used.add(fallback)
                    repaired = await execute_tool(fallback, {"query": goal, "include_web": True}, user_id=user_id, source="agent_repair")
                    run.record(step=idx, tool=fallback, repair=True, ok=not str(repaired).startswith("خطا"), result=redact_secrets(repaired)[:3000])
        except Exception as exc:
            logger.warning("V73 agent step failed: %s", exc, exc_info=True)
            run.record(step=idx, tool=tool, ok=False, error="internal_failure")
            if run.repairs < MAX_AGENT_REPAIRS:
                run.repairs += 1
        if (time.monotonic() - started) > 30:
            logger.warning("V73 agent slow step tool=%s", tool)

    return json.dumps({"ok": bool(run.steps), "goal": run.goal[:500], "steps": run.steps, "repairs": run.repairs}, ensure_ascii=False)[:9000]
