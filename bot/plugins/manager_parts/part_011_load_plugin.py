# Auto-split part 11: load_plugin
def load_plugin(name: str) -> bool:
    spec = _REGISTRY.get(name)
    if not spec or not spec.enabled:
        return False
    state = _STATE.setdefault(name, PluginState())
    if state.loaded:
        return True
    dep_error = _dependency_error(spec)
    if dep_error:
        state.load_error = dep_error
        state.last_error = dep_error
        state.healthy = False
        return False
    if not spec.module:
        state.loaded = True
        state.loaded_at = time.time()
        state.healthy = True
        return True
    try:
        module = importlib.import_module(spec.module)
        _HOOKS[name] = module
        state.loaded = True
        state.loaded_at = time.time()
        state.healthy = True
        return True
    except (ImportError, ModuleNotFoundError, AttributeError, RuntimeError) as exc:
        message = f"{type(exc).__name__}: {str(exc)[:180]}"
        state.load_error = message
        state.last_error = message
        state.healthy = False
        return False
