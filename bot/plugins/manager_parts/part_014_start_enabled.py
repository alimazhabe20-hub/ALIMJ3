# Auto-split part 14: start_enabled
def start_enabled() -> None:
    try:
        order = _load_order()
    except ValueError as exc:
        for state in _STATE.values():
            state.load_error = str(exc)
            state.last_error = str(exc)
            state.healthy = False
        return
    for name in order:
        spec = _REGISTRY[name]
        if not spec.enabled or not load_plugin(name):
            continue
        state = _STATE[name]
        if state.started:
            continue
        try:
            _call_hook(name, "on_start")
            state.started = True
            state.start_count += 1
            state.last_hook = "on_start"
        except (RuntimeError, ValueError, TypeError, OSError) as exc:
            state.last_error = f"start: {type(exc).__name__}: {str(exc)[:180]}"
            state.load_error = state.last_error
            state.healthy = False
