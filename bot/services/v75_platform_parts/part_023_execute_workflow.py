from typing import Any

# Auto-split part 23: execute_workflow
async def execute_workflow(name: str, steps: list[dict[str,Any]], *, user_id:int=0) -> dict[str,Any]:
    ok,reason=validate_workflow(steps)
    run_id=uuid.uuid4().hex
    if not ok: return {"ok":False,"run_id":run_id,"reason":reason}
    conn=_db(); conn.execute("INSERT INTO v75_workflow_runs(id,user_id,name,status,input_json) VALUES(?,?,?,?,?)",(run_id,user_id,name,"running",json.dumps(steps,ensure_ascii=False))); conn.commit(); conn.close()
    results=[]
    from bot.services.tool_runtime import execute_tool, get_registered_tool_names
    try:
        for step in steps:
            tool=str(step["tool"]); args=step.get("arguments",{}) or {}
            if tool not in get_registered_tool_names(): raise ValueError("unknown_tool")
            result=await execute_tool(tool,args,user_id=user_id)
            results.append({"tool":tool,"result":redact(result,2500)})
            if str(result).startswith(("خطا در اجرای","زمان اجرای","ابزار مسدود","ابزار ناشناخته")): raise RuntimeError("tool_failed")
        status="completed"
        payload={"ok":True,"run_id":run_id,"steps":results,"final":results[-1]["result"] if results else ""}
    except Exception:
        status="failed"; payload={"ok":False,"run_id":run_id,"steps":results,"reason":"workflow_failed"}
    conn=_db(); conn.execute("UPDATE v75_workflow_runs SET status=?,result_json=?,finished_at=CURRENT_TIMESTAMP WHERE id=?",(status,json.dumps(payload,ensure_ascii=False),run_id)); conn.commit(); conn.close()
    return payload
