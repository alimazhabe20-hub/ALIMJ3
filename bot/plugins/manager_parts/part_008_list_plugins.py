from typing import Any

# Auto-split part 8: list_plugins
def list_plugins() -> list[dict[str, Any]]:
    return [
        {
            "name": spec.name,
            "version": spec.version,
            "description": spec.description,
            "enabled": spec.enabled,
            "loaded": _STATE.get(spec.name, PluginState()).loaded,
            "started": _STATE.get(spec.name, PluginState()).started,
            "healthy": _STATE.get(spec.name, PluginState()).healthy,
            "error": _STATE.get(spec.name, PluginState()).load_error,
            "tags": list(spec.tags),
            "dependencies": list(spec.dependencies),
        }
        for spec in sorted(_REGISTRY.values(), key=lambda x: x.name)
    ]
