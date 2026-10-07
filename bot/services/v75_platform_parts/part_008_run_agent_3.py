from typing import Any

# Auto-split part 8: run_agent_3
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
