from typing import Any

# Auto-split part 49: plugin_snapshot
def plugin_snapshot() -> dict[str,Any]:
    return {k:{"version":v["version"],"permissions":sorted(v["permissions"]),"trusted":v["trusted"]} for k,v in _PLUGINS.items()}
