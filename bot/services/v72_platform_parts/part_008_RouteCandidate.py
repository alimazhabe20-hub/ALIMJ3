from dataclasses import dataclass

# Auto-split part 8: RouteCandidate
@dataclass(frozen=True)
class RouteCandidate:
    provider: str
    model: str
    score: float
    reason: str
