from typing import Any

# Auto-split part 9: run_agent_4
async def run_agent_4(goal: str, *, user_id: int = 0) -> dict[str, Any]:
    from bot.services.tool_runtime import execute_tool, get_registered_tool_names
    plan=build_plan(goal,get_registered_tool_names()); start=time.monotonic(); out=[]; seen=set()
    if not plan.steps: return {"ok": bool(plan.goal), "status":"direct_or_blocked", "plan":asdict(plan), "steps":[]}
    for idx,step in enumerate(plan.steps,1):
        if idx>MAX_STEPS or len(out)>=plan.max_calls or (time.monotonic()-start)*1000>=plan.budget_ms: break
        if step["tool"] in seen: continue
        seen.add(step["tool"]); t=time.monotonic()
        result=await execute_tool(step["tool"],step.get("arguments",{}),user_id=user_id,source="agent")
        ok=not str(result).startswith(("خطا در اجرای","زمان اجرای","ابزار ناشناخته","ابزار مسدود"))
        out.append({"step":idx,"tool":step["tool"],"ok":ok,"verified":ok,"latency_ms":round((time.monotonic()-t)*1000,1),"result":redact(result,3000)})
        record_performance("agent4:"+step["tool"],(time.monotonic()-t)*1000,ok)
        if not ok: break
    status="completed" if out and all(x["ok"] for x in out) else "partial" if out else "failed"
    return {"ok":status in {"completed","partial"},"status":status,"plan":asdict(plan),"steps":out,"elapsed_ms":round((time.monotonic()-start)*1000,1)}
