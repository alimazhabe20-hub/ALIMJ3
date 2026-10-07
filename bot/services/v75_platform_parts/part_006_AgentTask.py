from dataclasses import dataclass

# Auto-split part 6: AgentTask
@dataclass
class AgentTask:
    id: str
    goal: str
    steps: list[dict[str, Any]]
    status: str = "planned"
