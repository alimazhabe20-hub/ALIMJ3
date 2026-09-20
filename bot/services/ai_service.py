"""Stable public facade.

IMPORTANT: Keep this file small and stable. New functionality belongs in the
secondary ``ai_service_parts/`` modules. The complete legacy implementation is kept
unchanged in ``ai_service_parts/part_999_core_legacy.py`` for compatibility.
"""
from bot.utils.modular_loader import load_modular_part

load_modular_part(__file__, 'ai_service_parts/part_999_core_legacy.py')


import os
TTS_VOICE = os.getenv("TTS_VOICE", "fa-IR-DilaraNeural")
