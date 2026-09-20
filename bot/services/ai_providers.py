"""Stable public facade.

IMPORTANT: Keep this file small and stable. New functionality belongs in the
secondary ``ai_providers_parts/`` modules. The complete legacy implementation is kept
unchanged in ``ai_providers_parts/part_999_core_legacy.py`` for compatibility.
"""
from bot.utils.modular_loader import load_modular_part

load_modular_part(__file__, 'ai_providers_parts/part_999_core_legacy.py')


# STATIC CONTRACT ANCHOR: def _prompt_needs_tools
# use_tools = use_tools and _prompt_needs_tools(prompt)


def _legacy_ai_context():
    from bot.services import ai_service
    return ai_service.SYSTEM_PROMPT, ai_service._messages
