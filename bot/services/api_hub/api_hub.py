"""Resilient async execution layer for keyless public APIs."""
from __future__ import annotations

import asyncio
import hashlib
import json
import random
import time
from typing import Any
from urllib.parse import quote

import httpx

from bot.logger import logger
from .api_hub_registry import APIProvider, get_provider


class APIHub:
    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, Any]] = {}
        self._lock = asyncio.Lock()
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(12.0, connect=5.0),
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
                follow_redirects=True,
                headers={"User-Agent": "ALIMJBot/3.0 (+public-api-hub)"},
            )
        return self._client

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

    async def call(
        self,
        provider_name: str,
        *,
        params: dict[str, Any] | None = None,
        retries: int = 2,
        timeout: float | None = None,
    ) -> Any:
        provider = get_provider(provider_name)
        if provider is None:
            raise KeyError(f"Unknown API provider: {provider_name}")

        supplied = dict(params or {})
        merged_params = dict(provider.params)
        merged_params.update(supplied)
        url = provider.base_url
        for key, value in list(merged_params.items()):
            marker = "{" + key + "}"
            if marker in url:
                url = url.replace(marker, quote(str(value), safe=""))
                merged_params.pop(key, None)

        cache_key = self._cache_key(provider, merged_params)
        cached = await self._cache_get(cache_key)
        if cached is not None:
            return cached

        client = await self._get_client()
        last_error: Exception | None = None
        request_timeout = float(timeout or provider.timeout)

        for attempt in range(max(0, retries) + 1):
            try:
                response = await client.request(
                    provider.method,
                    url,
                    params=merged_params or None,
                    headers=provider.headers or None,
                    timeout=request_timeout,
                )
                if response.status_code in {408, 425, 429, 500, 502, 503, 504} and attempt < retries:
                    await asyncio.sleep(min(2.5, 0.25 * (2**attempt) + random.random() * 0.15))
                    continue
                response.raise_for_status()
                data = response.json()
                await self._cache_set(cache_key, data, provider.cache_ttl)
                return data
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt < retries:
                    await asyncio.sleep(min(2.5, 0.25 * (2**attempt) + random.random() * 0.15))
                    continue

        logger.warning("API Hub provider failed: %s (%s)", provider.name, last_error)
        raise last_error or RuntimeError(f"API provider failed: {provider.name}")

    async def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
        self._client = None
        self._cache.clear()


api_hub = APIHub()
