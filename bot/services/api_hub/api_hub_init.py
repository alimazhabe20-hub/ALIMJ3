"""Keyless public API hub for ALIMJ.

The hub centralizes public, no-API-key HTTP integrations with bounded retries,
TTL caching and per-provider fallback support. It is intentionally independent
from Telegram handlers so existing bot behavior remains stable.
"""
from .api_hub import APIHub, api_hub
from .api_hub_registry import get_provider, list_providers
from .api_hub_runtime import (
    api_call,
    get_weather,
    get_exchange_rate,
    get_country,
    search_books,
    get_random_joke,
)

__all__ = [
    "APIHub",
    "api_hub",
    "api_call",
    "get_provider",
    "list_providers",
    "get_weather",
    "get_exchange_rate",
    "get_country",
    "search_books",
    "get_random_joke",
]
