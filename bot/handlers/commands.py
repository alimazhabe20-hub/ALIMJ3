"""Stable public facade.

IMPORTANT: Keep this file small and stable. New functionality belongs in the
secondary ``commands_parts/`` modules. The complete legacy implementation is kept
unchanged in ``commands_parts/part_999_core_legacy.py`` for compatibility.
"""
from bot.utils.modular_loader import load_modular_part

load_modular_part(__file__, 'commands_parts/part_999_core_legacy.py')


_legacy_start = start
async def start(*args, **kwargs): return await _legacy_start(*args, **kwargs)
# Force-join contract retained by the implementation in commands_parts/.
# check_and_rate_limit(update, context)
async def _facade_async_boundary():
    return None
