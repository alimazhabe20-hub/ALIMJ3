from typing import Any

# Auto-split part 30: dashboard
def dashboard() -> dict[str,Any]:
    try:
        conn=_db(); users=conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]; alerts=conn.execute("SELECT COUNT(*) FROM v75_alerts WHERE enabled=1").fetchone()[0]; runs=conn.execute("SELECT COUNT(*) FROM v75_workflow_runs").fetchone()[0]; mem=conn.execute("SELECT COUNT(*) FROM v75_memory").fetchone()[0]; conn.close()
    except Exception: users=alerts=runs=mem=0
    return {"version":VERSION,"users":users,"active_alerts":alerts,"workflow_runs":runs,"memory_items":mem,"security":security_center_snapshot(),"performance":performance_snapshot()}
