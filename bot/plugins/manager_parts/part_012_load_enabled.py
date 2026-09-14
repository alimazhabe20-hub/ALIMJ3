# Auto-split part 12: load_enabled
def load_enabled() -> dict[str, bool]:
    try:
        order = _load_order()
    except ValueError as exc:
        return {name: False for name in _REGISTRY if _REGISTRY[name].enabled} | {"__error__": False}
    return {name: load_plugin(name) for name in order}
