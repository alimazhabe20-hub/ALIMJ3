"""Compatibility registry API kept for older integrations/tests.

The production registry lives in ``bot.services.api_hub.api_hub_registry``.
This adapter deliberately accepts only keyless providers so the old public
contract cannot be used to introduce API-keyed providers into the hub.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ApiProvider:
    key: str
    name: str
    category: str
    base_url: str
    auth: str = "No"
    method: str = "GET"
    timeout: float = 10.0
    cache_ttl: float = 30.0
    params: dict[str, Any] | None = None
    headers: dict[str, str] | None = None


def register_provider(provider: ApiProvider) -> ApiProvider:
    if str(provider.auth or "No").strip().lower() not in {"no", "none", "keyless", ""}:
        raise ValueError("API Hub accepts keyless providers only")
    # Compatibility-only registration. Production providers remain immutable
    # in the canonical registry to prevent accidental runtime mutation.
    return provider
