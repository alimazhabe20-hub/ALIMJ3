# Auto-split part 11: note_tool_failure
def note_tool_failure(name: str) -> bool:
    now = time.monotonic()
    q = _TOOL_FAILURES[name]
    q.append(now)
    recent = sum(1 for x in q if now - x <= 120)
    if recent >= max(3, int(os.getenv("V74_TOOL_FAILURE_THRESHOLD", "4"))):
        _TOOL_DISABLED_UNTIL[name] = now + max(10, int(os.getenv("V74_TOOL_COOLDOWN", "45")))
        return True
    return False
