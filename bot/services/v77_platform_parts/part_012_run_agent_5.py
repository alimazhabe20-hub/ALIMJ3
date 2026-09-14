from typing import Any

# Auto-split part 12: run_agent_5
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
