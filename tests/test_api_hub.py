from __future__ import annotations

import asyncio

from bot.services.api_hub import all_providers, get_provider, health_check
from bot.services.api_hub_parts.registry import ApiProvider, register_provider


def test_registry_contains_only_keyless_providers() -> None:
    providers = all_providers()
    assert providers
    assert all(p.auth == "No" for p in providers)


def test_known_provider_lookup() -> None:
    provider = get_provider("open_meteo")
    assert provider is not None
    assert provider.category == "weather"


def test_rejects_keyed_provider() -> None:
    try:
        register_provider(ApiProvider(
            key="should_fail",
            name="Should Fail",
            category="test",
            base_url="https://example.com",
            auth="apiKey",
        ))
    except ValueError:
        pass
    else:
        raise AssertionError("keyed providers must not be accepted by the keyless hub")


def test_health_check_shape() -> None:
    rows = asyncio.run(health_check())
    assert rows
    assert {"key", "category", "failures", "cooldown_seconds"}.issubset(rows[0])


def test_shopping_and_geocoding_providers_are_keyless() -> None:
    assert get_provider("onefindme_search").auth == "No"
    assert get_provider("nominatim_search").auth == "No"
    assert get_provider("nominatim_reverse").auth == "No"


def test_shopping_and_geocoding_runtime_exports() -> None:
    from bot.services.api_hub import search_products, geocode, reverse_geocode
    assert callable(search_products)
    assert callable(geocode)
    assert callable(reverse_geocode)


def test_sports_games_news_providers_are_keyless() -> None:
    assert get_provider("jolpica_f1").auth == "No"
    assert get_provider("freetogame_games").auth == "No"
    assert get_provider("freetogame_game").auth == "No"
    assert get_provider("spaceflight_news").auth == "No"


def test_sports_games_news_runtime_exports() -> None:
    from bot.services.api_hub import get_f1_data, search_games, get_game, search_spaceflight_news
    assert callable(get_f1_data)
    assert callable(search_games)
    assert callable(get_game)
    assert callable(search_spaceflight_news)
