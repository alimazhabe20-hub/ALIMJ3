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

def test_new_keyless_capabilities_are_registered() -> None:
    keys = {p.name for p in all_providers()}
    assert {"coin_gecko_simple", "itunes_search", "musicbrainz", "tvmaze_search", "nager_date"}.issubset(keys)

