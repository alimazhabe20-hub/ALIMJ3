"""Compatibility registry facade for older ALIMJ3 tests."""
from dataclasses import dataclass
from typing import Iterable
from bot.services.api_hub.api_hub_registry import APIProvider, PROVIDERS

@dataclass(frozen=True)
class ApiProvider:
    key: str
    name: str
    category: str
    base_url: str
    auth: str = "No"

def register_provider(provider: ApiProvider) -> None:
    if provider.auth != "No":
        raise ValueError("keyed providers are not allowed in the keyless API Hub")
    if provider.key in PROVIDERS:
        raise ValueError(f"provider already exists: {provider.key}")
    raise ValueError("runtime registration is intentionally disabled; edit the central registry")
