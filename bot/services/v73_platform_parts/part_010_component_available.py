# Auto-split part 10: component_available
def component_available(component: str) -> bool:
    return time.monotonic() >= _COOLDOWN_UNTIL.get(component, 0.0)
