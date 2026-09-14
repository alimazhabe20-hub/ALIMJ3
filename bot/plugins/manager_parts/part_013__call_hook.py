# Auto-split part 13: _call_hook
def _call_hook(name: str, hook: str) -> None:
    module = _HOOKS.get(name)
    fn: Callable[[], Any] | None = getattr(module, hook, None) if module else None
    if fn:
        fn()
