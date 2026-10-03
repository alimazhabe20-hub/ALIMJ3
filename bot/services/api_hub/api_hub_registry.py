"""Registry for public APIs that do not require an API key.

URLs are kept here instead of in handlers, making providers easy to replace
without changing the rest of the bot.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class APIProvider:
    name: str
    category: str
    base_url: str
    method: str = "GET"
    timeout: float = 10.0
    cache_ttl: float = 30.0
    params: dict[str, Any] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    description: str = ""

    @property
    def auth(self) -> str:
        """Compatibility marker: every registered provider is keyless."""
        return "No"


PROVIDERS: dict[str, APIProvider] = {
    "open_meteo_forecast": APIProvider(
        "open_meteo_forecast", "weather", "https://api.open-meteo.com/v1/forecast",
        cache_ttl=120, description="Current weather and forecast; no key required.",
    ),
    "open_meteo_geocoding": APIProvider(
        "open_meteo_geocoding", "geocoding", "https://geocoding-api.open-meteo.com/v1/search",
        cache_ttl=3600, description="City name to coordinates; no key required.",
    ),
    "frankfurter": APIProvider(
        "frankfurter", "currency", "https://api.frankfurter.app/latest",
        cache_ttl=60, description="Reference exchange rates; no key required.",
    ),
    "rest_countries": APIProvider(
        "rest_countries", "world", "https://restcountries.com/v3.1/name/{name}",
        cache_ttl=86400, description="Country information; no key required.",
    ),
    "rest_countries_all": APIProvider(
        "rest_countries_all", "world", "https://restcountries.com/v3.1/all",
        cache_ttl=86400, description="Country catalog; no key required.",
    ),
    "jokeapi": APIProvider(
        "jokeapi", "entertainment", "https://v2.jokeapi.dev/joke/Any",
        cache_ttl=30, description="Random jokes; no key required.",
    ),
    "quotable": APIProvider(
        "quotable", "quotes", "https://api.quotable.io/random",
        cache_ttl=30, description="Random quotes; no key required.",
    ),
    "open_library_search": APIProvider(
        "open_library_search", "books", "https://openlibrary.org/search.json",
        cache_ttl=300, description="Book search; no key required.",
    ),
    "gutendex": APIProvider(
        "gutendex", "books", "https://gutendex.com/books",
        cache_ttl=300, description="Public-domain books; no key required.",
    ),
    "musicbrainz": APIProvider(
        "musicbrainz", "music", "https://musicbrainz.org/ws/2/recording",
        cache_ttl=300, headers={"Accept": "application/json"},
        description="Music metadata search; no key required.",
    ),
    "itunes_search": APIProvider(
        "itunes_search", "music", "https://itunes.apple.com/search",
        cache_ttl=300, description="Music and media search; no key required.",
    ),
    "tvmaze_search": APIProvider(
        "tvmaze_search", "video", "https://api.tvmaze.com/search/shows",
        cache_ttl=300, description="TV show search; no key required.",
    ),
    "nager_date": APIProvider(
        "nager_date", "calendar", "https://date.nager.at/api/v3/PublicHolidays/{year}/{country_code}",
        cache_ttl=86400, description="Public holidays; no key required.",
    ),
    "coin_gecko_simple": APIProvider(
        "coin_gecko_simple", "crypto", "https://api.coingecko.com/api/v3/simple/price",
        cache_ttl=20, description="Crypto prices; no key required for public endpoint.",
    ),
    "ipma_weather": APIProvider(
        "ipma_weather", "weather", "https://api.ipma.pt/open-data/forecast/meteorology/cities/daily/{city_id}.json",
        cache_ttl=120, description="Portuguese weather data; no key required.",
    ),
}


# Stable aliases kept for older integrations/tests.
PROVIDER_ALIASES = {
    "open_meteo": "open_meteo_forecast",
}


def get_provider(name: str) -> APIProvider | None:
    name = str(name).strip().lower()
    name = PROVIDER_ALIASES.get(name, name)
    return PROVIDERS.get(str(name).strip().lower())


def list_providers(category: str | None = None) -> list[APIProvider]:
    values = list(PROVIDERS.values())
    if category:
        wanted = category.strip().lower()
        values = [item for item in values if item.category.lower() == wanted]
    return values
