import os
import sys
import types

from bot.plugins import manager
from bot.plugins.manager import PluginSpec, plugin_health, register, reset_registry_for_tests


def setup_function():
    reset_registry_for_tests()


def teardown_function():
    reset_registry_for_tests()


def test_builtin_dependencies_and_health():
    manager.register_builtin_plugins()
    result = manager.load_enabled()
    assert all(result.values())
    health = plugin_health()
    assert health["ok"] is True
    agents = next(x for x in health["plugins"] if x["name"] == "agents")
    assert agents["dependencies"] == ["ai", "knowledge"]


def test_disabled_dependency_blocks_dependent_plugin(monkeypatch):
    monkeypatch.setenv("PLUGINS_DISABLED", "ai")
    manager.register_builtin_plugins()
    manager.load_enabled()
    agents = next(x for x in manager.list_plugins() if x["name"] == "agents")
    assert agents["enabled"] is True
    assert agents["healthy"] is False
    assert "disabled dependency" in agents["error"]


def test_lifecycle_is_idempotent_and_reverse_order():
    events = []
    module_a = types.ModuleType("test_plugin_a")
    module_b = types.ModuleType("test_plugin_b")
    module_a.on_start = lambda: events.append("a:start")
    module_a.on_stop = lambda: events.append("a:stop")
    module_b.on_start = lambda: events.append("b:start")
    module_b.on_stop = lambda: events.append("b:stop")
    sys.modules[module_a.__name__] = module_a
    sys.modules[module_b.__name__] = module_b
    try:
        register(PluginSpec("a", "1", "A", module=module_a.__name__))
        register(PluginSpec("b", "1", "B", module=module_b.__name__, dependencies=("a",)))
        manager.start_enabled()
        manager.start_enabled()
        assert events == ["a:start", "b:start"]
        manager.stop_enabled()
        manager.stop_enabled()
        assert events == ["a:start", "b:start", "b:stop", "a:stop"]
    finally:
        sys.modules.pop(module_a.__name__, None)
        sys.modules.pop(module_b.__name__, None)


def test_hook_failure_is_isolated():
    module = types.ModuleType("test_plugin_failure")
    def boom():
        raise RuntimeError("boom")
    module.on_start = boom
    sys.modules[module.__name__] = module
    try:
        register(PluginSpec("bad", "1", "Bad", module=module.__name__))
        register(PluginSpec("good", "1", "Good"))
        manager.start_enabled()
        bad = next(x for x in manager.list_plugins() if x["name"] == "bad")
        good = next(x for x in manager.list_plugins() if x["name"] == "good")
        assert bad["healthy"] is False
        assert good["started"] is True
    finally:
        sys.modules.pop(module.__name__, None)
