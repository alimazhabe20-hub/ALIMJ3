"""Stable public facade.

IMPORTANT: Keep this file small and stable. New functionality belongs in the
secondary ``weather_parts/`` modules. The complete legacy implementation is kept
unchanged in ``weather_parts/part_999_core_legacy.py`` for compatibility.
"""
from bot.utils.modular_loader import load_modular_part

load_modular_part(__file__, 'weather_parts/part_999_core_legacy.py')


# Legacy alias contract: _get = _request_get
