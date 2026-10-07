from typing import Any

# Auto-split part 37: plugin_snapshot
def plugin_snapshot()->dict[str,Any]:return {k:{"version":v["version"],"permissions":sorted(v["permissions"])} for k,v in _PLUGINS.items()}
