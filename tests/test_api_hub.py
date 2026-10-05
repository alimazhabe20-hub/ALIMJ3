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


def test_movie_tv_providers_are_keyless() -> None:
    for name in ("tvmaze_search", "tvmaze_schedule", "tvmaze_web_schedule", "cinemeta_catalog_movies", "cinemeta_catalog_series"):
        assert get_provider(name).auth == "No"


def test_movie_tv_runtime_exports() -> None:
    from bot.services.api_hub import movie_tv_intelligence, search_tv, get_movie_catalog, get_series_catalog
    assert callable(movie_tv_intelligence)
    assert callable(search_tv)
    assert callable(get_movie_catalog)
    assert callable(get_series_catalog)


def test_registry_has_core_domains() -> None:
    categories = {p.category for p in all_providers()}
    required = {"anime", "games", "news", "science", "health", "security", "food", "animals", "dictionary", "text", "jobs", "development", "education", "vehicle", "transportation", "social"}
    assert required.issubset(categories)


def test_provider_status_is_real_state_shape() -> None:
    rows = asyncio.run(health_check())
    row = next(r for r in rows if r["key"] == "open_meteo_forecast")
    assert "health_score" in row
    assert "successes" in row
    assert "last_error" in row


def test_circuit_breaker_records_failures_and_recovers(monkeypatch) -> None:
    from bot.services.api_hub.api_hub import APIHub
    from bot.services.api_hub.api_hub_registry import get_provider
    hub = APIHub()
    hub._failure_threshold = 2
    hub._cooldown_seconds = 30
    err = RuntimeError("boom")
    hub._record_failure("open_meteo_forecast", err)
    hub._record_failure("open_meteo_forecast", err)
    status = next(x for x in hub.provider_status() if x["key"] == "open_meteo_forecast")
    assert status["healthy"] is False
    assert status["cooldown_seconds"] > 0
    hub._health["open_meteo_forecast"].cooldown_until = 0
    assert hub._is_available("open_meteo_forecast") is True


def test_smart_provider_selection() -> None:
    from bot.services.api_hub.api_hub import APIHub
    hub = APIHub()
    assert hub.choose_provider("weather") in {"open_meteo_forecast", "ipma_weather"}


def test_movie_intelligence_uses_real_query_provider(monkeypatch) -> None:
    from bot.services.api_hub import movie_tv_intelligence
    from bot.services.api_hub.api_hub_runtime import api_hub

    async def fake_call(name, *, params=None, **kwargs):
        assert name == "imdb_suggestion"
        assert params == {"query": "Inception"}
        return {"d": [{"id": "tt1375666", "l": "Inception", "y": 2010, "q": "feature", "rank": 1, "i": {"imageUrl": "https://example.invalid/inception.jpg"}}]}

    monkeypatch.setattr(api_hub, "call", fake_call)
    result = __import__("asyncio").run(movie_tv_intelligence(query="Inception", content_type="movie", limit=5))
    assert result["movies"][0]["imdb_id"] == "tt1375666"
    assert result["movies"][0]["title"] == "Inception"


def test_registry_has_no_fake_opencage_provider() -> None:
    from bot.services.api_hub import get_provider
    assert get_provider("opencage_placeholder") is None


def test_urlhaus_provider_has_valid_limit_path() -> None:
    from bot.services.api_hub import get_provider
    provider = get_provider("urlhaus")
    assert provider is not None
    assert provider.base_url.endswith("/recent/limit/10/")
