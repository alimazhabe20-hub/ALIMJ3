"""Shared imports and module state for the refactored ai_tools."""

from __future__ import annotations

"""Ordered compatibility loader for cleaned source chunks."""

"""Built-in AI tool handlers and public tool API.

Generic registry/execution machinery lives in tool_runtime.py. This facade
re-exports the historical public functions so existing imports are stable.
"""

import asyncio

import json

from typing import Any, List

from bot.services.tool_runtime import (
    register_tool, get_registered_tool_names, get_tool_definitions,
    _REGISTRY, _TOOL_CACHEABLE,
    parse_tool_arguments, execute_tool, gather_context_for_prompt,
    list_registered_tools, clear_tool_cache,
)

from bot.services.ai_tool_registry import register_builtin_tools

from bot.services.tool_runtime import register_tool as _register_tool
