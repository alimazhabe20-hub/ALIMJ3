"""Public API Hub facade for ALIMJ3."""
from .api_hub import APIHub, api_hub
from .api_hub_registry import APIProvider, get_provider, list_providers
from .api_hub_runtime import (
    api_call, get_weather, get_exchange_rate, get_country, search_books, get_random_joke,
)

def all_providers():
    return list_providers()

async def health_check():
    return api_hub.provider_status()

__all__ = [
    "APIHub", "APIProvider", "api_hub", "api_call", "get_provider", "list_providers",
    "all_providers", "health_check", "get_weather", "get_exchange_rate", "get_country",
    "search_books", "get_random_joke",
]
