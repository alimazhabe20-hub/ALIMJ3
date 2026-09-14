from dataclasses import dataclass

# Auto-split part 13: AgentStep
@dataclass
class AgentStep:
    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)
    reason: str = ""
