"""Stable facade for ALIMJ's public/keyless API hub.

New providers should be registered through ``api_hub_parts`` instead of being
called directly from Telegram handlers. Existing callers are unaffected.
"""
from __future__ import annotations

from .api_hub_parts.registry import (
    ApiProvider,
    all_providers,
    get_provider,
    providers_by_category,
    register_provider,
)
from .api_hub_parts.runtime import (
    ApiResult,
    call_json,
    health_check,
    invalidate_cache,
)

__all__ = [
    "ApiProvider",
    "ApiResult",
    "all_providers",
    "get_provider",
    "providers_by_category",
    "register_provider",
    "call_json",
    "health_check",
    "invalidate_cache",
]
