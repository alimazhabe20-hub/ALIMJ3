"""Runtime for keyless API providers: timeout, retries, cache and health."""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import urljoin

from bot.logger import logger
from bot.services.resilient_http import request_json

from .registry import get_provider


@dataclass(slots=True)
class ApiResult:
    ok: bool
    provider: str
    status: int = 0
    data: Any = None
    cached: bool = False
    stale: bool = False
    error: str = ""
    elapsed_ms: int = 0


_CACHE: dict[str, tuple[float, Any]] = {}
_CACHE_LOCK = asyncio.Lock()
_FAILURES: dict[str, int] = {}
_COOLDOWN_UNTIL: dict[str, float] = {}


def _cache_key(provider: str, path: str, params: Mapping[str, Any] | None) -> str:
    items = sorted((str(k), str(v)) for k, v in (params or {}).items())
    return f"{provider}|{path}|{items}"


async def _get_cached(key: str, ttl: int) -> tuple[Any, bool]:
    async with _CACHE_LOCK:
        item = _CACHE.get(key)
    if not item:
        return None, False
    created, value = item
    return value, (time.monotonic() - created) <= ttl


async def _put_cache(key: str, value: Any) -> None:
    async with _CACHE_LOCK:
        _CACHE[key] = (time.monotonic(), value)
        if len(_CACHE) > 1024:
            oldest = sorted(_CACHE.items(), key=lambda x: x[1][0])[:128]
            for k, _ in oldest:
                _CACHE.pop(k, None)


async def invalidate_cache(provider: str | None = None) -> None:
    async with _CACHE_LOCK:
        if not provider:
            _CACHE.clear()
            return
        prefix = provider.strip().lower() + "|"
        for key in list(_CACHE):
            if key.startswith(prefix):
                _CACHE.pop(key, None)


async def call_json(
    provider: str,
    path: str = "/",
    *,
    params: Mapping[str, Any] | None = None,
    method: str = "GET",
    retries: int = 1,
    timeout: float | None = None,
    cache_ttl: int | None = None,
    allow_stale: bool = True,
) -> ApiResult:
    spec = get_provider(provider)
    started = time.monotonic()
    if spec is None:
        return ApiResult(False, provider, error="provider_not_registered")
    if not spec.enabled:
        return ApiResult(False, provider, error="provider_disabled")
    now = time.monotonic()
    if _COOLDOWN_UNTIL.get(spec.key, 0) > now:
        key = _cache_key(spec.key, path, params)
        value, fresh = await _get_cached(key, cache_ttl if cache_ttl is not None else spec.cache_ttl)
        if value is not None and allow_stale:
            return ApiResult(True, spec.key, cached=True, stale=not fresh, data=value,
                             elapsed_ms=int((time.monotonic() - started) * 1000))
        return ApiResult(False, spec.key, error="provider_cooldown",
                         elapsed_ms=int((time.monotonic() - started) * 1000))

    key = _cache_key(spec.key, path, params)
    ttl = spec.cache_ttl if cache_ttl is None else max(0, int(cache_ttl))
    value, fresh = await _get_cached(key, ttl)
    if value is not None and fresh:
        return ApiResult(True, spec.key, cached=True, data=value,
                         elapsed_ms=int((time.monotonic() - started) * 1000))

    url = urljoin(spec.base_url.rstrip("/") + "/", path.lstrip("/"))
    try:
        status, data = await request_json(
            method, url, client_name=f"api-hub:{spec.key}",
            timeout=float(timeout or spec.timeout), retries=max(0, int(retries)),
            params=dict(params or {}),
        )
        if 200 <= status < 300:
            _FAILURES.pop(spec.key, None)
            _COOLDOWN_UNTIL.pop(spec.key, None)
            await _put_cache(key, data)
            return ApiResult(True, spec.key, status=status, data=data,
                             elapsed_ms=int((time.monotonic() - started) * 1000))
        failures = _FAILURES.get(spec.key, 0) + 1
        _FAILURES[spec.key] = failures
        if failures >= 3:
            _COOLDOWN_UNTIL[spec.key] = time.monotonic() + 30
        if value is not None and allow_stale:
            return ApiResult(True, spec.key, status=status, data=value, cached=True, stale=True,
                             error=f"http_{status}",
                             elapsed_ms=int((time.monotonic() - started) * 1000))
        return ApiResult(False, spec.key, status=status, error=f"http_{status}",
                         elapsed_ms=int((time.monotonic() - started) * 1000))
    except Exception as exc:
        failures = _FAILURES.get(spec.key, 0) + 1
        _FAILURES[spec.key] = failures
        if failures >= 3:
            _COOLDOWN_UNTIL[spec.key] = time.monotonic() + 30
        logger.warning("api_hub provider=%s error=%s", spec.key, exc)
        if value is not None and allow_stale:
            return ApiResult(True, spec.key, cached=True, stale=True, data=value,
                             error="request_failed",
                             elapsed_ms=int((time.monotonic() - started) * 1000))
        return ApiResult(False, spec.key, error="request_failed",
                         elapsed_ms=int((time.monotonic() - started) * 1000))


async def health_check(*, enabled_only: bool = True) -> list[dict[str, Any]]:
    """Return lightweight health data without hitting every provider endpoint."""
    from .registry import all_providers
    now = time.monotonic()
    rows: list[dict[str, Any]] = []
    for provider in all_providers(enabled_only=enabled_only):
        cooldown = max(0, int(_COOLDOWN_UNTIL.get(provider.key, 0) - now))
        rows.append({
            "key": provider.key,
            "name": provider.name,
            "category": provider.category,
            "enabled": provider.enabled,
            "failures": _FAILURES.get(provider.key, 0),
            "cooldown_seconds": cooldown,
        })
    return rows
