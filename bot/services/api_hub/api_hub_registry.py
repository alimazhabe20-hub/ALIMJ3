"""Provider registry for public APIs.

The registry is deliberately independent from Telegram handlers. Providers
can be enabled/disabled without changing the UI layer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class ApiProvider:
    key: str
    name: str
    category: str
    base_url: str
    auth: str = "No"
    enabled: bool = True
    timeout: float = 12.0
    cache_ttl: int = 60
    tags: tuple[str, ...] = field(default_factory=tuple)
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "category": self.category,
            "base_url": self.base_url,
            "auth": self.auth,
            "enabled": self.enabled,
            "timeout": self.timeout,
            "cache_ttl": self.cache_ttl,
            "tags": list(self.tags),
            "notes": self.notes,
        }


_PROVIDERS: dict[str, ApiProvider] = {}


def register_provider(provider: ApiProvider) -> ApiProvider:
    if provider.auth not in {"No", "none", ""}:
        raise ValueError(f"api_hub only accepts keyless providers: {provider.key}")
    _PROVIDERS[provider.key] = provider
    return provider


def get_provider(key: str) -> ApiProvider | None:
    return _PROVIDERS.get((key or "").strip().lower())


def all_providers(*, enabled_only: bool = False) -> list[ApiProvider]:
    values = list(_PROVIDERS.values())
    if enabled_only:
        values = [x for x in values if x.enabled]
    return sorted(values, key=lambda x: (x.category, x.name.lower()))


def providers_by_category(category: str, *, enabled_only: bool = True) -> list[ApiProvider]:
    wanted = (category or "").strip().casefold()
    return [
        x for x in all_providers(enabled_only=enabled_only)
        if x.category.casefold() == wanted
    ]


# First-wave, verified catalog entries used by the hub itself. More providers
# are added as adapters are implemented; catalog-only entries must not be
# exposed as working features until their endpoint contract is tested.
register_provider(ApiProvider(
    key="open_meteo",
    name="Open-Meteo",
    category="weather",
    base_url="https://api.open-meteo.com",
    cache_ttl=300,
    tags=("weather", "forecast", "geocoding"),
))
register_provider(ApiProvider(
    key="frankfurter",
    name="Frankfurter",
    category="currency",
    base_url="https://api.frankfurter.app",
    cache_ttl=300,
    tags=("currency", "forex", "exchange"),
))
register_provider(ApiProvider(
    key="coingecko",
    name="CoinGecko",
    category="crypto",
    base_url="https://api.coingecko.com",
    cache_ttl=30,
    tags=("crypto", "price", "market"),
))
register_provider(ApiProvider(
    key="rest_countries",
    name="REST Countries",
    category="geocoding",
    base_url="https://restcountries.com",
    cache_ttl=86400,
    tags=("country", "capital", "currency", "timezone"),
))
register_provider(ApiProvider(
    key="open_library",
    name="Open Library",
    category="books",
    base_url="https://openlibrary.org",
    cache_ttl=3600,
    tags=("books", "authors", "isbn"),
))
register_provider(ApiProvider(
    key="gutendex",
    name="Gutendex",
    category="books",
    base_url="https://gutendex.com",
    cache_ttl=3600,
    tags=("books", "public-domain"),
))
register_provider(ApiProvider(
    key="jikan",
    name="Jikan",
    category="anime",
    base_url="https://api.jikan.moe",
    cache_ttl=900,
    tags=("anime", "manga", "mal"),
))
register_provider(ApiProvider(
    key="studio_ghibli",
    name="Studio Ghibli API",
    category="anime",
    base_url="https://ghibliapi.vercel.app",
    cache_ttl=86400,
    tags=("anime", "films", "ghibli"),
))
register_provider(ApiProvider(
    key="dog_ceo",
    name="Dog CEO",
    category="animals",
    base_url="https://dog.ceo",
    cache_ttl=300,
    tags=("dogs", "images"),
))
register_provider(ApiProvider(
    key="cat_facts",
    name="Cat Facts",
    category="animals",
    base_url="https://catfact.ninja",
    cache_ttl=900,
    tags=("cats", "facts"),
))
register_provider(ApiProvider(
    key="quotable",
    name="Quotable",
    category="personality",
    base_url="https://api.quotable.io",
    cache_ttl=900,
    tags=("quotes", "authors"),
))
register_provider(ApiProvider(
    key="jokeapi",
    name="JokeAPI",
    category="entertainment",
    base_url="https://v2.jokeapi.dev",
    cache_ttl=300,
    tags=("jokes", "entertainment"),
))
register_provider(ApiProvider(
    key="quickchart",
    name="QuickChart",
    category="development",
    base_url="https://quickchart.io",
    cache_ttl=60,
    tags=("charts", "qr", "images"),
))
