# Auto-split part 9: note_failure
def note_failure(component: str) -> bool:
    now = time.monotonic()
    q = _FAILURES[component]
    q.append(now)
    threshold = max(2, int(os.getenv("V73_FAILURE_THRESHOLD", "3")))
    if len([x for x in q if now - x <= 120]) >= threshold:
        _COOLDOWN_UNTIL[component] = now + max(5, float(os.getenv("V73_COOLDOWN_SECONDS", "30")))
        return True
    return False
