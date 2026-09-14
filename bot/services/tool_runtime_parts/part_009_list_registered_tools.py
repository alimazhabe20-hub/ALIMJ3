from typing import List

# Auto-split part 9: list_registered_tools
def list_registered_tools() -> List[str]:
    return sorted(_REGISTRY.keys())
