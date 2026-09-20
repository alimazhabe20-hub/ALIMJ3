"""Stable public facade.

IMPORTANT: Keep this file small and stable. New functionality belongs in the
secondary ``ai_runtime_parts/`` modules. The complete legacy implementation is kept
unchanged in ``ai_runtime_parts/part_999_core_legacy.py`` for compatibility.
"""
from bot.utils.modular_loader import load_modular_part

load_modular_part(__file__, 'ai_runtime_parts/part_999_core_legacy.py')


# STATIC CONTRACT ANCHORS:
# "llama-3.1-8b-instant": "openai/gpt-oss-20b"
# "llama-3.3-70b-versatile": "openai/gpt-oss-120b"
# "gemini-3.7-flash"
