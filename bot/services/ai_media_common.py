"""Shared imports and module state for the refactored ai_media."""


"""Ordered compatibility loader for cleaned source chunks."""

"""Media, voice, image, music and video helpers for AI service.

Kept separate from the main AI router to keep modules focused and easier to test.
Runtime dependencies are imported from ai_service after its initialization.
"""

import asyncio

import base64

import os

import re

from pathlib import Path

from urllib.parse import quote

from typing import List, Optional

import httpx

from bot.logger import logger

from bot.utils.observability import record as record_metric

from bot.utils.task_manager import spawn

from bot.services import ai_service as _ai

TIMEOUT = _ai.TIMEOUT

MAX_OUTPUT = _ai.MAX_OUTPUT

GEMINI_SAFETY_SETTINGS = _ai.GEMINI_SAFETY_SETTINGS

IMAGE_GEN_MODEL = _ai.IMAGE_GEN_MODEL

IMAGE_GEN_MODEL_FALLBACKS = _ai.IMAGE_GEN_MODEL_FALLBACKS

TTS_VOICE = _ai.TTS_VOICE

_next_keys = _ai._next_keys

_advance_rr = _ai._advance_rr

_call_provider = _ai._call_provider

_get_http = _ai._get_http

_post_json = _ai._post_json

_is_quota_error = _ai._is_quota_error

_mark_key_cooldown = _ai._mark_key_cooldown

available_model_options = _ai.available_model_options

_LOCAL_PIPELINE = None

_LOCAL_PIPELINE_MODEL = None

_LOCAL_BACKEND_CACHE = None

from bot.services import ai_service as _ai
