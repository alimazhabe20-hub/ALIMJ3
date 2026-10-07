"""Stable public facade.

IMPORTANT: Keep this file small and stable. New functionality belongs in the
secondary ``keyboard_factory_parts/`` modules. The complete legacy implementation is kept
unchanged in ``keyboard_factory_parts/part_999_core_legacy.py`` for compatibility.
"""
from bot.utils.modular_loader import load_modular_part

load_modular_part(__file__, 'keyboard_factory_parts/part_999_core_legacy.py')


# STATIC CONTRACT ANCHORS — implementation lives in keyboard_factory_parts/.
# def get_more_keyboard():
# def get_date_tools_keyboard():
# def get_smart_settings_keyboard():
# 🔄 بررسی بروزرسانی
# def get_country_keyboard():
