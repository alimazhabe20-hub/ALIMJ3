from pathlib import Path
from typing import Any

# Auto-split part 62: system_snapshot
def system_snapshot(root: str|Path=".") -> dict[str,Any]:
    try:c=_db();users=c.execute("SELECT COUNT(*) FROM users").fetchone()[0];alerts=c.execute("SELECT COUNT(*) FROM v77_alerts WHERE enabled=1").fetchone()[0];nodes=c.execute("SELECT COUNT(*) FROM v77_graph_nodes").fetchone()[0];c.close()
    except Exception:users=alerts=nodes=0
    return {"version":VERSION,"users":users,"active_alerts":alerts,"graph_nodes":nodes,"security":security_center(),"performance":performance_snapshot(),"providers":provider_snapshot(),"plugins":plugin_snapshot(),"self_healing":self_healing_snapshot()}
