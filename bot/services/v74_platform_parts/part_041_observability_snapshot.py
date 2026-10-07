from typing import Any

# Auto-split part 41: observability_snapshot
def observability_snapshot() -> dict[str, Any]:
    return {
        "version": VERSION,
        "agent": {"limits": {"steps": MAX_AGENT_STEPS, "calls": MAX_AGENT_CALLS, "repairs": MAX_AGENT_REPAIRS}},
        "performance": performance_snapshot(),
        "healing": healing_snapshot(),
        "providers": provider_snapshot(),
        "runtime": runtime_snapshot(),
        "tools": tool_policy_snapshot(),
        "persistence": persistence_snapshot(),
    }
