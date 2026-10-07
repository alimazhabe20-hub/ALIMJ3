# Auto-split part 10: tool_allowed
def tool_allowed(name: str, *, source: str = "system", approved: bool = False) -> tuple[bool, str]:
    p = _TOOL_POLICIES.get(name)
    if p and not p.enabled:
        return False, "disabled"
    if p and time.monotonic() < _TOOL_DISABLED_UNTIL.get(name, 0):
        return False, "cooldown"
    if p and p.risk in {"write", "admin"} and source in {"agent", "agent_repair"} and not approved:
        return False, "approval_required"
    return True, "ok"
