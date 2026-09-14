# Auto-split part 4: run_agent
async def run_agent(goal: str, *, user_id: int = 0) -> str:
    """Plan, execute, and perform one bounded repair attempt."""
    goal = (goal or "").strip()
    if not goal:
        return "هدف خالی است."
    plan = build_plan(goal)
    if not plan:
        return "برای این درخواست برنامه ابزارمحور مطمئنی پیدا نشد؛ پاسخ مستقیم AI مناسب‌تر است."

    from bot.services.ai_tools import execute_tool, get_registered_tool_names
    from bot.services.agent_learning import record, should_prefer_fallback
    available = get_registered_tool_names()
    results: list[dict[str, Any]] = []
    repairs = 0
    for index, step in enumerate(plan, 1):
        tool = step["tool"]
        args = dict(step.get("arguments") or {})
        if tool not in available:
            return f"برنامه متوقف شد: ابزار {tool} در دسترس نیست."
        try:
            effective_tool = tool
            learned_from = None
            fallback_map = {
                "get_weather": "hybrid_retrieve",
                "get_air_quality": "hybrid_retrieve",
                "get_market_prices": "hybrid_retrieve",
                "search_shopping": "hybrid_retrieve",
                "search_knowledge_base": "hybrid_retrieve",
            }
            if should_prefer_fallback(user_id, "general", tool) and fallback_map.get(tool) in available:
                effective_tool = fallback_map[tool]
                learned_from = tool
            value = await execute_tool(effective_tool, args if effective_tool != "hybrid_retrieve" else {"query": goal, "include_web": True}, user_id=user_id)
            failed = isinstance(value, str) and value.startswith(("خطا در اجرای", "زمان اجرای", "ابزار ناشناخته"))
            record(user_id, "general", tool, not failed, "tool failure" if failed else "")
            if failed and repairs < MAX_REPAIRS:
                repairs += 1
                fallback = "get_user_city" if tool in {"get_weather", "get_air_quality"} and not args.get("city") else None
                if fallback and fallback in available:
                    city = await execute_tool(fallback, {}, user_id=user_id)
                    retry_args = dict(args)
                    if city and not str(city).startswith(("خطا", "ابزار ناشناخته")):
                        retry_args["city"] = str(city).strip()
                        value = await execute_tool(tool, retry_args, user_id=user_id)
                        results.append({"step": index, "tool": tool, "executed_tool": effective_tool, "learned_from": learned_from, "repaired": True, "result": str(value)[:3000]})
                        continue
            results.append({"step": index, "tool": tool, "executed_tool": effective_tool, "learned_from": learned_from, "repaired": repairs > 0 and failed, "result": str(value)[:3000]})
        except Exception as exc:
            logger.warning("agent step %s failed: %s", index, exc, exc_info=True)
            if repairs >= MAX_REPAIRS:
                return str({"ok": False, "failed_step": index, "steps": results})[:7000]
            repairs += 1
            results.append({"step": index, "tool": tool, "repaired": False, "error": str(exc)[:800]})

    return str({"ok": True, "goal": goal[:500], "steps": results, "repairs": repairs})[:7000]
