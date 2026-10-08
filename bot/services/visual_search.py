"""ALIMJ Visual Lens - API-free visual/product search helper.

Features
--------
* Optional local vision model (BLIP via transformers/torch).
* Optional local OCR (Tesseract + Pillow).
* Multi-query web retrieval using DuckDuckGo HTML (no API key).
* Soft ranking: exact match is NOT required; similar results are kept.
* Safe fallbacks when optional ML dependencies/models are unavailable.

Environment variables
---------------------
LOCAL_VISION_MODEL_PATH : local HuggingFace model directory. If empty, the
                          vision model is disabled unless an existing cached
                          Transformers model can be loaded by name.
LOCAL_VISION_MODEL      : model id/name, default Salesforce/blip-image-captioning-base.
TESSERACT_CMD            : path to tesseract executable, if not on PATH.
VISION_MAX_QUERIES       : maximum web queries, default 7.
VISION_MAX_RESULTS       : results per query, default 6.
VISION_HTTP_TIMEOUT      : HTTP timeout, default 12 seconds.
VISION_SEARCH_REGION     : DuckDuckGo region, default wt-wt.
"""

from __future__ import annotations
from bot.utils.modular_loader import load_modular_part

import asyncio
import html
import io
import os
import re
import shutil
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Iterable, Optional
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import httpx

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None


DEFAULT_VISION_MODEL = os.getenv(
    "LOCAL_VISION_MODEL", "Salesforce/blip-image-captioning-base"
)
LOCAL_VISION_MODEL_PATH = os.getenv("LOCAL_VISION_MODEL_PATH", "").strip()
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "").strip()
MAX_QUERIES = max(3, int(os.getenv("VISION_MAX_QUERIES", "7")))
MAX_RESULTS_PER_QUERY = max(3, int(os.getenv("VISION_MAX_RESULTS", "6")))
HTTP_TIMEOUT = float(os.getenv("VISION_HTTP_TIMEOUT", "12"))
SEARCH_REGION = os.getenv("VISION_SEARCH_REGION", "wt-wt")


load_modular_part(__file__, 'visual_search_parts/part_001_SearchResult.py')


_STOPWORDS = {
    "و", "در", "از", "با", "برای", "به", "یک", "این", "آن", "است", "که",
    "را", "روی", "داخل", "شده", "شود", "می", "های", "the", "a", "an", "of",
    "and", "with", "for", "to", "in", "on", "this", "that", "is", "are", "image",
    "photo", "picture", "product", "find", "search", "similar", "item",
}


load_modular_part(__file__, 'visual_search_parts/part_002__normalize.py')


load_modular_part(__file__, 'visual_search_parts/part_003__tokens.py')


load_modular_part(__file__, 'visual_search_parts/part_004__unique.py')


load_modular_part(__file__, 'visual_search_parts/part_005__extract_keywords.py')


load_modular_part(__file__, 'visual_search_parts/part_006__image_info.py')


load_modular_part(__file__, 'visual_search_parts/part_007__ocr.py')


# BLIP is deliberately lazy-loaded: normal bot startup does not import torch.
_VISION_STATE: dict[str, Any] = {"ready": False, "failed": False, "processor": None, "model": None}


load_modular_part(__file__, 'visual_search_parts/part_008__vision_model_source.py')


load_modular_part(__file__, 'visual_search_parts/part_009__load_vision_model.py')


load_modular_part(__file__, 'visual_search_parts/part_010__vision_caption.py')


load_modular_part(__file__, 'visual_search_parts/part_011__strip_ddg_url.py')


load_modular_part(__file__, 'visual_search_parts/part_012__clean_html.py')


load_modular_part(__file__, 'visual_search_parts/part_013__ddg_search.py')


load_modular_part(__file__, 'visual_search_parts/part_014__query_variants.py')


load_modular_part(__file__, 'visual_search_parts/part_015__score_result.py')


load_modular_part(__file__, 'visual_search_parts/part_016__dedupe_and_rank.py')


load_modular_part(__file__, 'visual_search_parts/part_017_looks_like_visual_search.py')


load_modular_part(__file__, 'visual_search_parts/part_018_visual_search.py')


__all__ = ["visual_search", "looks_like_visual_search"]
