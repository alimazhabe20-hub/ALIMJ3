"""Stable public facade.

IMPORTANT: Keep this file small and stable. New functionality belongs in the
secondary ``ai_media_parts/`` modules. The complete legacy implementation is kept
unchanged in ``ai_media_parts/part_999_core_legacy.py`` for compatibility.
"""
from bot.utils.modular_loader import load_modular_part

load_modular_part(__file__, 'ai_media_parts/part_999_core_legacy.py')


from bot.services import ai_service as _ai
TTS_VOICE = _ai.TTS_VOICE
