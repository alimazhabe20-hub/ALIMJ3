from pathlib import Path
from typing import Any

# Auto-split part 57: admin_snapshot
def admin_snapshot(root: str|Path=".") -> dict[str,Any]:
    return {"version":VERSION,"security":security_center(),"performance":performance_snapshot(),"providers":provider_snapshot(),"plugins":plugin_snapshot(),"self_healing":self_healing_snapshot(),"release_gate":release_gate(root)}
