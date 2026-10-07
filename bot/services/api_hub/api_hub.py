"""Resilient async execution layer for keyless public APIs.

Includes cache, bounded retry/backoff, per-provider health tracking, circuit
breakers and deterministic fallback chains.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import random
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx

from bot.logger import logger
from .api_hub_registry import APIProvider, get_provider


@dataclass
class _Health: 
    failures: int = 0
    successes: int = 0
    latency_ms: float = 0.0
    last_error: str | None = None
    last_ok: float = 0.0
    cooldown_until: float = 0.0

    @property
    def healthy(self) -> bool:
        return self.cooldown_until <= time.monotonic()

    @property
    def score(self) -> float:
        total = self.successes + self.failures
        reliability = self.successes / total if total else 1.0
        latency_factor = 1.0 / (1.0 + max(0.0, self.latency_ms) / 1000.0)
        return round(reliability * latency_factor * (0.15 if not self.healthy else 1.0), 4)


FALLBACK_CHAINS: dict[str, tuple[str, ...]] = {
    "weather": ("open_meteo_forecast", "ipma_weather"),
    "books": ("open_library_search", "gutendex"),
    "music": ("itunes_search", "musicbrainz"),
    "video": ("tvmaze_search", "cinemeta_catalog_movies", "cinemeta_catalog_series"),
    "quotes": ("quotable", "jokeapi"),
    "news": ("spaceflight_news",),
    "science": ("europe_pmc", "gbif"),
    "security": ("nvd_cves", "urlhaus"),
}


class APIHub:
    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, Any]] = {}
        self._lock = asyncio.Lock()
        self._client: httpx.AsyncClient | None = None
        self._health: dict[str, _Health] = {}
        self._failure_threshold = 3
        self._cooldown_seconds = 30.0

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(12.0, connect=5.0),
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
                follow_redirects=True,
                headers={"User-Agent": "ALIMJBot/3.0 (+public-api-hub)"},
            )
        return self._client

    def _state(self, name: str) -> _Health:
        return self._health.setdefault(name, _Health())

    @staticmethod
    def _cache_key(provider: APIProvider, params: dict[str, Any]) -> str:
        payload = json.dumps(params, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(f"{provider.name}|{payload}".encode()).hexdigest()

    async def _cache_get(self, key: str) -> Any:
        async with self._lock:
            item = self._cache.get(key)
            if not item:
                return None
            expires, value = item
            if expires <= time.monotonic():
                self._cache.pop(key, None)
                return None
            return value

    async def _cache_set(self, key: str, value: Any, ttl: float) -> None:
        if ttl <= 0:
            return
        async with self._lock:
            self._cache[key] = (time.monotonic() + ttl, value)
            if len(self._cache) > 1024:
                now = time.monotonic()
                expired = [k for k, (expires, _) in self._cache.items() if expires <= now]
                for k in expired[:256]:
                    self._cache.pop(k, None)

    def _record_success(self, name: str, latency_ms: float) -> None:
        state = self._state(name)
        state.successes += 1
        state.failures = 0
        state.last_ok = time.monotonic()
        state.last_error = None
        state.latency_ms = latency_ms if not state.latency_ms else (state.latency_ms * 0.7 + latency_ms * 0.3)
        state.cooldown_until = 0.0

    def _record_failure(self, name: str, exc: Exception) -> None:
        state = self._state(name)
        state.failures += 1
        state.last_error = f"{type(exc).__name__}: {exc}"[:300]
        if state.failures >= self._failure_threshold:
            state.cooldown_until = time.monotonic() + self._cooldown_seconds

    def _is_available(self, name: str) -> bool:
        return self._state(name).healthy

    async def call(self, provider_name: str, *, params: dict[str, Any] | None = None, retries: int = 2, timeout: float | None = None) -> Any:
        provider = get_provider(provider_name)
        if provider is None:
            raise KeyError(f"Unknown API provider: {provider_name}")
        supplied = dict(params or {})
        merged = dict(provider.params)
        merged.update(supplied)
        url = provider.base_url
        for key, value in list(merged.items()):
            marker = "{" + key + "}"
            if marker in url:
                url = url.replace(marker, quote(str(value), safe=""))
                merged.pop(key, None)
        cache_key = self._cache_key(provider, merged)
        cached = await self._cache_get(cache_key)
        if cached is not None:
            return cached
        if not self._is_available(provider.name):
            raise RuntimeError(f"Provider temporarily in cooldown: {provider.name}")
        client = await self._get_client()
        last_error: Exception | None = None
        request_timeout = float(timeout or provider.timeout)
        for attempt in range(max(0, retries) + 1):
            started = time.perf_counter()
            try:
                response = await client.request(provider.method, url, params=merged or None, headers=provider.headers or None, timeout=request_timeout)
                if response.status_code in {408, 425, 429, 500, 502, 503, 504}:
                    raise httpx.HTTPStatusError(f"retryable status {response.status_code}", request=response.request, response=response)
                response.raise_for_status()
                data = response.json()
                self._record_success(provider.name, (time.perf_counter() - started) * 1000)
                await self._cache_set(cache_key, data, provider.cache_ttl)
                return data
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                self._record_failure(provider.name, exc)
                if attempt < retries:
                    await asyncio.sleep(min(3.0, 0.3 * (2 ** attempt) + random.random() * 0.2))
        logger.warning("API Hub provider failed: %s (%s)", provider.name, last_error)
        raise last_error or RuntimeError(f"API provider failed: {provider.name}")

    async def call_with_fallback(self, providers: list[str] | tuple[str, ...], *, params: dict[str, Any] | None = None, retries: int = 1) -> Any:
        errors: list[str] = []
        for name in providers:
            if not get_provider(name) or not self._is_available(name):
                continue
            try:
                return await self.call(name, params=params, retries=retries)
            except Exception as exc:
                errors.append(f"{name}: {type(exc).__name__}")
        raise RuntimeError("All API providers failed: " + ", ".join(errors))

    def choose_provider(self, category: str, *, candidates: list[str] | tuple[str, ...] | None = None) -> str | None:
        from .api_hub_registry import list_providers
        names = list(candidates or [p.name for p in list_providers(category)])
        names = [n for n in names if get_provider(n) and self._is_available(n)]
        if not names:
            return None
        return max(names, key=lambda n: self._state(n).score)

    def provider_status(self) -> list[dict[str, Any]]:
        from .api_hub_registry import list_providers
        now = time.monotonic()
        rows = []
        for provider in list_providers():
            state = self._state(provider.name)
            rows.append({
                "key": provider.name, "category": provider.category,
                "failures": state.failures, "successes": state.successes,
                "latency_ms": round(state.latency_ms, 2), "health_score": state.score,
                "cooldown_seconds": max(0.0, round(state.cooldown_until - now, 2)),
                "healthy": state.healthy, "last_error": state.last_error,
                "checked_at": now,
            })
        return rows

    async def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
        self._client = None
        self._cache.clear()
        self._health.clear()


api_hub = APIHub()
