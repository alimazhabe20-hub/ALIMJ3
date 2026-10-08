"""Utility compatibility layer for the flattened deployment."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import sys

def load_modular_part(owner_file, relative_path):
    """Load an optional modular part without allowing it to crash startup."""
    owner = Path(owner_file).resolve()
    target = (owner.parent / relative_path).resolve()
    if not target.is_file():
        return None
    name = f"_alimj_part_{abs(hash(str(target)))}"
    try:
        spec = importlib.util.spec_from_file_location(name, str(target))
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _install_legacy_aliases():
    """Expose legacy flattened module paths without requiring duplicate files."""
    import importlib
    aliases = {
        "bot.utils.events": "bot.utils.utils_events",
        "bot.features.date.converters": "bot.features.date.features_date_converters",
        "bot.features.date.date_tools": "bot.features.date.features_date_date_tools",
        "bot.features.fun.fun_tools": "bot.features.fun.features_fun_fun_tools",
        "bot.features.tools.app_tools": "bot.features.tools.features_tools_app_tools",
        "bot.features.weather.weather": "bot.features.weather.features_weather_weather",
        "bot.features.weather.weather_extra": "bot.features.weather.features_weather_weather_extra",
        "bot.api.weather": "bot.api.api_weather",
        "bot.api.weather_extra": "bot.api.api_weather_extra",
    }
    for legacy, target in aliases.items():
        if legacy in sys.modules:
            continue
        try:
            sys.modules[legacy] = importlib.import_module(target)
        except Exception:
            # Keep startup resilient; the normal import path remains available.
            continue

_install_legacy_aliases()
