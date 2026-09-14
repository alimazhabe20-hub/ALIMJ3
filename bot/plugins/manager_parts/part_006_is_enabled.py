# Auto-split part 6: is_enabled
def is_enabled(name: str) -> bool:
    spec = _REGISTRY.get(name)
    return bool(spec and spec.enabled)
