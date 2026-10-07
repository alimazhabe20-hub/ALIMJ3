from dataclasses import dataclass

# Auto-split part 6: Plan
@dataclass
class Plan:
    id: str
    goal: str
    steps: list[dict[str, Any]]
    budget_ms: int = 60000
    max_calls: int = MAX_CALLS
