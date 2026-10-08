"""Automatic AI capability discovery and registration.

New features can expose tools in either of these ways:

1) Decorator (preferred for new code)::

    from bot.services.capability_autoload import ai_tool

    @ai_tool(
        name="my_feature",
        description="...",
        parameters={...},
        keywords=[r"کلمه.?کلیدی"],
    )
    def my_feature(...):
        ...

2) Module-level list ``__ai_tools__`` in any importable module under
   ``bot.features`` or ``bot.services``::

    __ai_tools__ = [
        {
            "name": "my_feature",
            "description": "...",
            "parameters": {...},
            "handler": my_feature,
            "keywords": [r"..."],
        },
    ]

3) Central bridge ``bot.services.ai_full_bridge`` which wires existing
   feature functions that predate the decorator.

On bot startup / first tool use, ``ensure_all_capabilities_registered()``
imports discovery targets and registers every tool into the shared
``tool_runtime`` registry so the model sees them automatically.
"""

import importlib
import logging
import pkgutil
from typing import Any, Callable, Optional

logger = logging.getLogger("rooze_ziba")

_ENSURED = False
_ENSURING = False
_PENDING_DECORATED: list[dict[str, Any]] = []

# Packages scanned for __ai_tools__ / @ai_tool modules.
_DISCOVERY_PACKAGES = (
    "bot.features",
    "bot.services",
)

# Explicit modules that always register full capability bridges.
_BRIDGE_MODULES = (
    "bot.services.ai_full_bridge",
)

# Core tool facade. This module contains the actual built-in tool registrations
# (including search_shopping). It must be imported before bridge/discovery so
# those tools are present in the shared registry. Importing it while ENSURING is
# safe because its own autoload call becomes a no-op.
_CORE_TOOL_MODULES = (
    "bot.services.ai_tools",
)


def ai_tool(
    *,
    name: str,
    description: str,
    parameters: Optional[dict] = None,
    keywords: Optional[list] = None,
    risk: str = "read",
    network: bool = False,
) -> Callable:
    """Decorator: mark a function as an AI tool (auto-registered on ensure)."""

    def decorator(fn: Callable) -> Callable:
        meta = {
            "name": name,
            "description": description,
            "parameters": parameters or {"type": "object", "properties": {}},
            "handler": fn,
            "keywords": keywords or [],
            "risk": risk,
            "network": network,
        }
        setattr(fn, "__ai_tool_meta__", meta)
        _PENDING_DECORATED.append(meta)
        # If registry is already live, register immediately.
        try:
            _register_one(meta)
        except Exception as exc:
            logger.debug("ai_tool early register skipped for %s: %s", name, exc)
        return fn

    return decorator


def _register_one(meta: dict[str, Any]) -> None:
    from bot.services.tool_runtime import register_tool, get_registered_tool_names

    name = meta["name"]
    if name in get_registered_tool_names():
        return
    register_tool(
        name=name,
        description=meta.get("description") or name,
        parameters=meta.get("parameters") or {"type": "object", "properties": {}},
        handler=meta["handler"],
        keywords=meta.get("keywords") or [],
        risk=meta.get("risk") or "read",
        network=bool(meta.get("network")),
    )


def _register_from_module(mod: Any) -> int:
    count = 0
    # 1) __ai_tools__ list
    items = getattr(mod, "__ai_tools__", None)
    if isinstance(items, (list, tuple)):
        for item in items:
            if not isinstance(item, dict) or "name" not in item or "handler" not in item:
                continue
            try:
                _register_one(item)
                count += 1
            except Exception as exc:
                logger.warning("capability register failed %s: %s", item.get("name"), exc)

    # 2) functions with __ai_tool_meta__
    for attr in dir(mod):
        try:
            obj = getattr(mod, attr)
        except Exception:
            continue
        meta = getattr(obj, "__ai_tool_meta__", None)
        if isinstance(meta, dict) and "name" in meta:
            try:
                _register_one(meta)
                count += 1
            except Exception as exc:
                logger.warning("capability register failed %s: %s", meta.get("name"), exc)
    return count


def _walk_package(pkg_name: str) -> int:
    count = 0
    try:
        pkg = importlib.import_module(pkg_name)
    except Exception as exc:
        logger.debug("capability package import skipped %s: %s", pkg_name, exc)
        return 0
    paths = getattr(pkg, "__path__", None)
    if not paths:
        return _register_from_module(pkg)

    prefix = pkg_name + "."
    for modinfo in pkgutil.walk_packages(paths, prefix):
        name = modinfo.name
        # Skip heavy / test / private noise
        if any(x in name for x in (".tests", ".test_", ".__", "_parts.part_")):
            # Still allow explicit ai_bind modules
            if not name.endswith(".ai_bind") and ".ai_tools" not in name:
                continue
        try:
            mod = importlib.import_module(name)
            count += _register_from_module(mod)
        except Exception as exc:
            logger.debug("capability module skip %s: %s", name, exc)
    return count


def ensure_all_capabilities_registered() -> dict:
    """Idempotently register all AI capabilities without recursive re-entry."""
    global _ENSURED, _ENSURING
    result = {"decorated": 0, "bridges": 0, "discovered": 0, "total": 0, "added": []}

    # tool_runtime helpers call back into this function. During registration
    # that callback must be a no-op, otherwise bridge registration recurses
    # until Python raises ``maximum recursion depth exceeded``.
    if _ENSURED:
        try:
            from bot.services.tool_runtime import _orig_get_registered_tool_names
            names = set(_orig_get_registered_tool_names())
            result["total"] = len(names)
        except Exception:
            pass
        return result
    if _ENSURING:
        return result
    _ENSURING = True
    try:
        # Load the stable AI tool facade first. Its module-level registrations
        # are the source of truth for built-in capabilities such as shopping.
        for mod_name in _CORE_TOOL_MODULES:
            try:
                importlib.import_module(mod_name)
            except Exception as exc:
                logger.warning("core AI tool module load failed %s: %s", mod_name, exc)

        from bot.services.tool_runtime import get_registered_tool_names

        before = set(get_registered_tool_names())
    except Exception:
        before = set()

    # Pending @ai_tool decorators
    for meta in list(_PENDING_DECORATED):
        try:
            _register_one(meta)
            result["decorated"] += 1
        except Exception as exc:
            logger.warning("decorated tool failed: %s", exc)

    # Explicit bridges (missing legacy features)
    for mod_name in _BRIDGE_MODULES:
        try:
            mod = importlib.import_module(mod_name)
            if hasattr(mod, "register"):
                mod.register()
            result["bridges"] += _register_from_module(mod)
        except Exception as exc:
            logger.warning("bridge load failed %s: %s", mod_name, exc)

    # Discover feature/service modules
    if not _ENSURED:
        for pkg in _DISCOVERY_PACKAGES:
            result["discovered"] += _walk_package(pkg)

    try:
        from bot.services.tool_runtime import get_registered_tool_names

        after = set(get_registered_tool_names())
        result["total"] = len(after)
        result["added"] = sorted(after - before)
    except Exception:
        pass

    _ENSURED = True
    logger.info(
        "AI capabilities ready: total=%s decorated=%s bridges=%s discovered=%s",
        result.get("total"),
        result["decorated"],
        result["bridges"],
        result["discovered"],
    )
    _ENSURING = False
    return result
