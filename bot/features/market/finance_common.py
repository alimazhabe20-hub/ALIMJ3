"""Shared imports and module state for the refactored finance."""

"""Ordered compatibility loader for cleaned source chunks."""

"""
مالی و بازار — ارز، فلزات، سکه + کریپتو کامل
نمودار قیمت + مبدل همه ارزهای دیجیتال + تحلیل چندمنبعی (CoinGecko + Binance + CoinPaprika + Fear&Greed + تلاش Coinglass)
"""

import re

import io

import asyncio

from datetime import datetime, timedelta

from typing import Optional, Tuple, List, Dict, Any

import httpx

from bs4 import BeautifulSoup

from bot.config import config

from bot.logger import logger

from bot.utils.http_resilience import pooled_client

from bot.utils.http_client import pooled_async_client, request_with_retry, safe_json

_cache = {}

_cache_t = {}

_cache_locks = {}

_HTTP_DATA_CACHE = {}

_HTTP_DATA_CACHE_T = {}

MARKET_CACHE_TTLS = {
    "price": 5, "klines": 15, "indicators": 30, "derivatives": 20,
    "fundamentals": 300, "macro": 300, "news": 120, "onchain": 180,
    "calendar": 1800, "market_context": 60,
}

_HTTP_DATA_CACHE_TTL = 30

_HTTP_DATA_CACHE_MAX = 256

from bot.features.market.finance_core import (
    TGJU_SLUGS, SYMBOL_TO_ID, pn, _parse_price, _fetch_tgju_bulk, _tgju_price,
    _get_usd_rial, resolve_coin_id, _crypto_simple, _top_from_coinlore,
    _top_from_paprika, get_crypto_price, get_top_crypto, convert_crypto, full_market_prices,
    rial_toman, convert_currency, profit_loss, parse_profit, parse_currency_input,
)
