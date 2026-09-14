# Auto-split part 1: _enabled
def _enabled() -> bool:
    return bool(getattr(config, "AUTO_REACTIONS_ENABLED", True))
