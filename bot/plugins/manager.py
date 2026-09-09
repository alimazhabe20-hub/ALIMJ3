"""Safe local plugin registry with dependency-aware lifecycle management."""
from __future__ import annotations

import importlib
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict


@dataclass(frozen=True)
class PluginSpec:
    name: str
    version: str
    description: str
    module: str = ""
    enabled: bool = True
    tags: tuple[str, ...] = field(default_factory=tuple)
    dependencies: tuple[str, ...] = field(default_factory=tuple)


@dataclass
class PluginState:
    loaded: bool = False
    load_error: str = ""
    started: bool = False
    stopped: bool = False
    loaded_at: float = 0.0
    start_count: int = 0
    stop_count: int = 0
    last_hook: str = ""
    last_error: str = ""
    healthy: bool = True


_REGISTRY: Dict[str, PluginSpec] = {}
_STATE: Dict[str, PluginState] = {}
_HOOKS: Dict[str, object] = {}


def _disabled_names() -> set[str]:
    raw = os.getenv("PLUGINS_DISABLED", "")
    return {x.strip().lower() for x in raw.split(",") if x.strip()}


def register(spec: PluginSpec) -> PluginSpec:
    if not spec.name or not spec.name.replace("_", "").isalnum():
        raise ValueError("Invalid plugin name")
    disabled = _disabled_names()
    if spec.name.lower() in disabled:
        spec = PluginSpec(
            spec.name, spec.version, spec.description, spec.module,
            False, spec.tags, spec.dependencies,
        )
    _REGISTRY[spec.name] = spec
    _STATE.setdefault(spec.name, PluginState())
    return spec


def register_builtin_plugins() -> None:
    specs = (
        PluginSpec("ai", "40.x", "AI providers, routing and context", tags=("core", "ai")),
        PluginSpec("weather", "40.x", "Weather and air-quality features", tags=("feature",)),
        PluginSpec("market", "40.x", "Market and crypto features", tags=("feature",)),
        PluginSpec("media", "40.x", "Image, voice and media AI features", tags=("feature", "ai"), dependencies=("ai",)),
        PluginSpec("knowledge", "40.x", "Knowledge base and retrieval", tags=("rag",), dependencies=("ai",)),
        PluginSpec("agents", "40.x", "Workflow, autonomous and multi-agent execution", tags=("agent",), dependencies=("ai", "knowledge")),
        PluginSpec("automation", "40.x", "Scheduled proactive assistant", tags=("automation",)),
    )
    for spec in specs:
        register(spec)


def is_enabled(name: str) -> bool:
    spec = _REGISTRY.get(name)
    return bool(spec and spec.enabled)


def _dependency_error(spec: PluginSpec) -> str:
    missing = [dep for dep in spec.dependencies if dep not in _REGISTRY]
    disabled = [dep for dep in spec.dependencies if dep in _REGISTRY and not _REGISTRY[dep].enabled]
    failed = [dep for dep in spec.dependencies if dep in _STATE and _STATE[dep].load_error]
    if missing:
        return "missing dependency: " + ", ".join(missing)
    if disabled:
        return "disabled dependency: " + ", ".join(disabled)
    if failed:
        return "failed dependency: " + ", ".join(failed)
    return ""


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


def plugin_health() -> dict[str, Any]:
    """Return a safe summary suitable for diagnostics/health endpoints."""
    items = list_plugins()
    unhealthy = [item["name"] for item in items if item["enabled"] and not item["healthy"]]
    return {"ok": not unhealthy, "total": len(items), "unhealthy": unhealthy, "plugins": items}


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


def load_enabled() -> dict[str, bool]:
    try:
        order = _load_order()
    except ValueError as exc:
        return {name: False for name in _REGISTRY if _REGISTRY[name].enabled} | {"__error__": False}
    return {name: load_plugin(name) for name in order}


def _call_hook(name: str, hook: str) -> None:
    module = _HOOKS.get(name)
    fn: Callable[[], Any] | None = getattr(module, hook, None) if module else None
    if fn:
        fn()


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


def reset_registry_for_tests() -> None:
    _REGISTRY.clear()
    _STATE.clear()
    _HOOKS.clear()
