"""Stable public facade for the AI service.

The implementation lives in ``ai_service_parts/part_999_core_legacy.py`` while
provider/runtime state lives in ``ai_runtime``. This facade keeps all historical
imports used by handlers stable across modular deployments.
"""
from bot.utils.modular_loader import load_modular_part

load_modular_part(__file__, "ai_service_parts/part_999_core_legacy.py")

import os
TTS_VOICE = os.getenv("TTS_VOICE", "fa-IR-DilaraNeural")

# Explicit public contract required by callbacks, messages and other handlers.
# These aliases come from the canonical runtime module.
from bot.services.ai_runtime import (
    clear_history,
    available_providers,
    set_selected_provider,
    get_selected_model,
)
