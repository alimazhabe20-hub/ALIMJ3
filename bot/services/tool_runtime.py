"""AI tool registry and execution runtime.

Built-in handlers remain in ai_tools.py; this module owns the generic runtime
so adding tools does not require growing the execution engine.
"""
from __future__ import annotations
from bot.utils.modular_loader import load_modular_part
import inspect
import json
import re
import asyncio
import os
import time
from typing import Any, Callable, Dict, List, Optional
from bot.logger import logger
from bot.utils.observability import record as record_metric

_REGISTRY: Dict[str, dict] = {}
_TOOL_INFLIGHT: Dict[str, asyncio.Task] = {}
_TOOL_INFLIGHT_LOCK = asyncio.Lock()
_TOOL_SEMAPHORE = asyncio.Semaphore(max(2, int(os.getenv("AI_TOOL_CONCURRENCY", "8"))))
_TOOL_CACHE: Dict[tuple, tuple[float, str]] = {}
_TOOL_CACHE_TTL = max(5, int(os.getenv("AI_TOOL_CACHE_TTL", "20")))
_TOOL_TIMEOUT = max(5.0, float(os.getenv("AI_TOOL_TIMEOUT", "25")))
_TOOL_CACHE_MAX = max(64, int(os.getenv("AI_TOOL_CACHE_MAX", "1024")))
_TOOL_CACHEABLE = {
    "get_weather", "get_weather_forecast", "get_air_quality",
    "get_market_prices", "get_top_crypto", "get_user_city", "get_economic_calendar",
}


load_modular_part(__file__, 'tool_runtime_parts/part_001_register_tool.py')


load_modular_part(__file__, 'tool_runtime_parts/part_002_get_registered_tool_names.py')


load_modular_part(__file__, 'tool_runtime_parts/part_003_get_tool_definitions.py')


load_modular_part(__file__, 'tool_runtime_parts/part_004_parse_tool_arguments.py')


load_modular_part(__file__, 'tool_runtime_parts/part_005_execute_tool.py')


load_modular_part(__file__, 'tool_runtime_parts/part_006_select_capability_tool.py')


load_modular_part(__file__, 'tool_runtime_parts/part_007__normalize_capability_text.py')


load_modular_part(__file__, 'tool_runtime_parts/part_008_gather_context_for_prompt.py')


load_modular_part(__file__, 'tool_runtime_parts/part_009_list_registered_tools.py')


load_modular_part(__file__, 'tool_runtime_parts/part_010_clear_tool_cache.py')
