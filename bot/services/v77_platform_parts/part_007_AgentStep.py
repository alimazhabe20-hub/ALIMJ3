from dataclasses import dataclass

# Auto-split part 7: AgentStep
@dataclass
class AgentStep:
    id: str
    tool: str
    arguments: dict[str, Any]
    depends_on: list[str]
    verify: bool = True
    retries: int = 1
