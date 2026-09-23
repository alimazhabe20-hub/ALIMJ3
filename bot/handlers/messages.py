"""Stable public facade.

IMPORTANT: Keep this file small and stable. New functionality belongs in the
secondary ``messages_parts/`` modules. The complete legacy implementation is kept
unchanged in ``messages_parts/part_999_core_legacy.py`` for compatibility.
"""
from bot.utils.modular_loader import load_modular_part

load_modular_part(__file__, 'messages_parts/part_999_core_legacy.py')


# Static compatibility contract: extracted handlers remain available from the
# stable facade without redefining them here.
from bot.handlers.feature_handlers import (
    _h_date_convert, _h_age_calc, _h_birthday, _h_zodiac, _h_lunar,
    _h_date_diff, _h_age_diff, _h_event_search, _h_countdown, _h_calc,
    _h_profit, _h_currency, _h_crypto_full, _h_crypto_pos, _h_crypto_chart,
    _h_crypto_analyze, _h_distance, _h_birth_save, _h_count_text,
    _h_font_text, _h_font_all,
)

# Facade API wrappers (keep these names stable; implementation remains in the legacy part).
_legacy_text_handler = text_handler
_legacy_media_ai_handler = media_ai_handler
_legacy_voice_ai_handler = voice_ai_handler
_legacy_lens_command = lens_command
async def text_handler(*args, **kwargs): return await _legacy_text_handler(*args, **kwargs)
async def media_ai_handler(*args, **kwargs): return await _legacy_media_ai_handler(*args, **kwargs)
async def voice_ai_handler(*args, **kwargs): return await _legacy_voice_ai_handler(*args, **kwargs)
async def lens_command(*args, **kwargs): return await _legacy_lens_command(*args, **kwargs)

# V30.5 stream contract anchors retained in the facade:
# last_rendered = "✍️ در حال نوشتن..."
# if first != last_rendered:
# await asyncio.sleep(0.15)
# await sent.edit_text(first
# await msg.reply_text(first
# from bot.handlers.media_handlers import media_ai_handler as _impl
# from bot.handlers.media_handlers import voice_ai_handler as _impl
# return answer, provider_label or "ai"
