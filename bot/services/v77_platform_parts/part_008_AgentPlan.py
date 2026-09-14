from dataclasses import dataclass

# Auto-split part 8: AgentPlan
@dataclass
class AgentPlan:
    id: str
    goal: str
    steps: list[AgentStep]
    budget_ms: int = 90000
    max_calls: int = MAX_CALLS
