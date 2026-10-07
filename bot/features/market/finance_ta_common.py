"""Shared imports and module state for the refactored finance_ta."""

from __future__ import annotations

import asyncio

from bot.features.market import finance as _f

from bot.logger import logger

from bot.utils.http_client import pooled_async_client, request_with_retry, safe_json

_fetch_klines_interval = _f._fetch_klines_interval
