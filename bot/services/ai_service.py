"""Stable public facade.

IMPORTANT: Keep this file small and stable. New functionality belongs in the
secondary ``ai_service_parts/`` modules. The complete legacy implementation is kept
unchanged in ``ai_service_parts/part_999_core_legacy.py`` for compatibility.
"""
from bot.utils.modular_loader import load_modular_part

load_modular_part(__file__, 'ai_service_parts/part_999_core_legacy.py')


import os
TTS_VOICE = os.getenv("TTS_VOICE", "fa-IR-DilaraNeural")

# Stable compatibility exports.
# The callbacks module imports these public helpers directly from ai_service.
# Keep the facade explicit so a stale/partial modular AI service fragment cannot
# make the whole bot fail during startup.
try:
    from bot.services.ai_runtime import (
        clear_history,
        available_providers,
        set_selected_provider,
        get_selected_model,
    )
except Exception:
    # Preserve the original modular implementation as a fallback when the
    # runtime package itself is unavailable during an unusual partial deploy.
    pass
