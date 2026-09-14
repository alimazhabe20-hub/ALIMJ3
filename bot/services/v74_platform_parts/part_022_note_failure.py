# Auto-split part 22: note_failure
def note_failure(component: str, error: str = "") -> bool:
    now = time.monotonic(); q = _FAILURES[component]; q.append(now)
    threshold = max(3, int(os.getenv("V74_FAILURE_THRESHOLD", "4")))
    tripped = sum(1 for x in q if now-x <= 120) >= threshold
    if tripped:
        _RECOVERY_LOG.append({"component": component, "action": "cooldown", "error": redact_secrets(error)[:500], "at": time.time()})
    return tripped
