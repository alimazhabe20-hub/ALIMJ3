# Auto-split part 6: AgentRun
class AgentRun:
    def __init__(self, goal: str, user_id: int = 0):
        self.goal = goal[:6000]
        self.user_id = user_id
        self.started = time.monotonic()
        self.steps: list[dict[str, Any]] = []
        self.used: set[str] = set()
        self.calls = 0
        self.repairs = 0

    def can_call(self, tool: str) -> bool:
        return self.calls < MAX_TOOL_CALLS_PER_RUN and tool not in self.used

    def record(self, **item: Any) -> None:
        self.steps.append({**item, "elapsed_ms": round((time.monotonic() - self.started) * 1000, 1)})
