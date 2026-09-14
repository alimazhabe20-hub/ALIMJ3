# Auto-split part 10: _load_order
def _load_order() -> list[str]:
    result: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(name: str) -> None:
        if name in visited:
            return
        if name in visiting:
            raise ValueError(f"Plugin dependency cycle at {name}")
        visiting.add(name)
        spec = _REGISTRY[name]
        for dep in spec.dependencies:
            if dep in _REGISTRY and _REGISTRY[dep].enabled:
                visit(dep)
        visiting.remove(name)
        visited.add(name)
        result.append(name)

    for name, spec in _REGISTRY.items():
        if spec.enabled:
            visit(name)
    return result
