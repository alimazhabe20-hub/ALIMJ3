"""Stable public facade.

IMPORTANT: Keep this file small and stable. New functionality belongs in the
secondary ``callbacks_parts/`` modules. The complete legacy implementation is kept
unchanged in ``callbacks_parts/part_999_core_legacy.py`` for compatibility.
"""
from bot.utils.modular_loader import load_modular_part

load_modular_part(__file__, 'callbacks_parts/part_999_core_legacy.py')


_legacy_button_handler = button_handler
async def button_handler(*args, **kwargs): return await _legacy_button_handler(*args, **kwargs)
