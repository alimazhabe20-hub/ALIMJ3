"""Stable public facade.

IMPORTANT: Keep this file small and stable. New functionality belongs in the
secondary ``motivation_parts/`` modules. The complete legacy implementation is kept
unchanged in ``motivation_parts/part_999_core_legacy.py`` for compatibility.
"""
from bot.utils.modular_loader import load_modular_part

load_modular_part(__file__, 'motivation_parts/part_999_core_legacy.py')

