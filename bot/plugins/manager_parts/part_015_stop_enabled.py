# Auto-split part 15: stop_enabled
def stop_enabled() -> None:
    try:
        order = _load_order()
    except ValueError:
        order = list(_REGISTRY)
    for name in reversed(order):
        spec = _REGISTRY[name]
        if not spec.enabled:
            continue
        state = _STATE[name]
        if not state.started:
            continue
        try:
            _call_hook(name, "on_stop")
            state.last_hook = "on_stop"
        except (RuntimeError, ValueError, TypeError, OSError) as exc:
            state.last_error = f"stop: {type(exc).__name__}: {str(exc)[:180]}"
            state.load_error = state.last_error
            state.healthy = False
        finally:
            state.stopped = True
            state.stop_count += 1
            state.started = False
