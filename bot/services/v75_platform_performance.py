"""v75_platform: performance responsibilities."""
from .v75_platform_common import *  # noqa: F401,F403
from . import v75_platform_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def record_perf(component: str, latency_ms: float, ok: bool=True) -> None:
    _PERF[component].append((time.time(), float(latency_ms), bool(ok)))
    try:
        conn=_db(); conn.execute("INSERT INTO v75_metrics(component,operation,latency_ms,ok) VALUES(?,?,?,?)",(component,"runtime",float(latency_ms),1 if ok else 0)); conn.commit(); conn.close()
    except Exception: pass

def performance_snapshot() -> dict[str, Any]:
    out={}
    for name, rows in _PERF.items():
        vals=[r[1] for r in rows]; out[name]={"count":len(rows),"avg_ms":round(sum(vals)/len(vals),2) if vals else 0,"p95_ms":round(sorted(vals)[max(0,int(len(vals)*.95)-1)],2) if vals else 0,"errors":sum(not r[2] for r in rows)}
    return out

def qa_snapshot(root: str | Path = ".") -> dict[str, Any]:
    root=Path(root); files=list(root.rglob("*.py")) if root.exists() else []
    bad=[]
    for p in files:
        try: ast.parse(p.read_text(encoding="utf-8"),filename=str(p))
        except Exception: bad.append(str(p))
    return {"ok":not bad,"python_files":len(files),"syntax_errors":bad[:20],"security":security_center_snapshot(),"performance":performance_snapshot()}

def validate_workflow(steps: list[dict[str, Any]]) -> tuple[bool,str]:
    if not isinstance(steps,list) or not steps: return False,"workflow_empty"
    if len(steps)>MAX_WORKFLOW_STEPS: return False,"workflow_too_long"
    for i,s in enumerate(steps,1):
        if not isinstance(s,dict) or not str(s.get("tool") or "").strip(): return False,f"invalid_step_{i}"
        if s.get("tool") == "run_workflow": return False,"nested_workflow"
    return True,"ok"

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
