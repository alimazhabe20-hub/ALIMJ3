"""Public keyless API Hub facade."""
from .api_hub import APIHub, api_hub
from .api_hub_registry import APIProvider, get_provider, list_providers, PROVIDERS
from .api_hub_runtime import (
    api_call,
    get_weather,
    get_exchange_rate,
    get_country,
    search_books,
    get_random_joke,
    get_crypto_prices,
    search_music,
    search_music_metadata,
    search_tv,
    get_public_holidays,
)


def all_providers():
    return list_providers()


async def health_check():
    return api_hub.provider_status()


__all__ = [
    "APIHub", "api_hub", "APIProvider", "PROVIDERS", "get_provider", "list_providers", "all_providers",
    "health_check", "api_call", "get_weather", "get_exchange_rate", "get_country", "search_books",
    "get_random_joke", "get_crypto_prices", "search_music", "search_music_metadata", "search_tv",
    "get_public_holidays",
]
