"""Safe local plugin registry with dependency-aware lifecycle management."""
from __future__ import annotations
from bot.utils.modular_loader import load_modular_part

import importlib
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict


load_modular_part(__file__, 'manager_parts/part_001_PluginSpec.py')


load_modular_part(__file__, 'manager_parts/part_002_PluginState.py')


_REGISTRY: Dict[str, PluginSpec] = {}
_STATE: Dict[str, PluginState] = {}
_HOOKS: Dict[str, object] = {}


load_modular_part(__file__, 'manager_parts/part_003__disabled_names.py')


load_modular_part(__file__, 'manager_parts/part_004_register.py')


load_modular_part(__file__, 'manager_parts/part_005_register_builtin_plugins.py')


load_modular_part(__file__, 'manager_parts/part_006_is_enabled.py')


load_modular_part(__file__, 'manager_parts/part_007__dependency_error.py')


load_modular_part(__file__, 'manager_parts/part_008_list_plugins.py')


load_modular_part(__file__, 'manager_parts/part_009_plugin_health.py')


load_modular_part(__file__, 'manager_parts/part_010__load_order.py')


load_modular_part(__file__, 'manager_parts/part_011_load_plugin.py')


load_modular_part(__file__, 'manager_parts/part_012_load_enabled.py')


load_modular_part(__file__, 'manager_parts/part_013__call_hook.py')


load_modular_part(__file__, 'manager_parts/part_014_start_enabled.py')


load_modular_part(__file__, 'manager_parts/part_015_stop_enabled.py')


load_modular_part(__file__, 'manager_parts/part_016_reset_registry_for_tests.py')
