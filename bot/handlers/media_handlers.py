"""Media and voice Telegram handlers extracted from messages.py (V25).

async def media_ai_handler  # source-contract marker
async def voice_ai_handler  # source-contract marker

The public handler names remain available from bot.handlers.messages via thin
compatibility wrappers, so existing registrations and imports continue to work.
"""
from __future__ import annotations
from bot.utils.modular_loader import load_modular_part

from io import BytesIO
import re

from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers.middleware import check_and_rate_limit
from bot.logger import logger
from bot.services.ai_service import (
    _extract_text_from_bytes, ask_ai_media, analyze_video, generate_or_edit_image,
    looks_like_image_edit, speech_to_text,
    analyze_voice_emotion, should_auto_voice_reply, wants_voice_reply,
    wants_voice_chat_mode, wants_end_voice_chat, is_voice_only_request,
    translate_voice, wants_emotion_analysis,
)
from bot.services.ai_extras import enhance_ocr_prompt
from bot.services.visual_search import looks_like_visual_search
from bot.features.market.shopping import search_shopping
from bot.services.visual_search import visual_search
from bot.utils.helpers import get_ai_keyboard

load_modular_part(__file__, 'media_handlers_parts/part_001_media_ai_handler.py')


load_modular_part(__file__, 'media_handlers_parts/part_002_voice_ai_handler.py')

