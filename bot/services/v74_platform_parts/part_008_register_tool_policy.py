from typing import Any
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from bot.services.v74_platform import ToolPolicy

# Auto-split part 8: register_tool_policy
def register_tool_policy(name: str, **kwargs: Any) -> ToolPolicy:
    policy = ToolPolicy(name=name, **{k: v for k, v in kwargs.items() if k in ToolPolicy.__dataclass_fields__})
    _TOOL_POLICIES[name] = policy
    return policy
