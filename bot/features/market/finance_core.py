"""Core market pricing, conversion and crypto-list operations extracted from finance.py.

This module is intentionally independent of the large finance facade. Public
legacy function names remain re-exported by ``finance.py`` for compatibility.
"""
from __future__ import annotations
from bot.utils.modular_loader import load_modular_part

import asyncio
import re
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup
import httpx

from bot.logger import logger
from bot.utils.http_client import pooled_async_client, request_with_retry, safe_json

_cache = {}
_cache_t = {}
_cache_locks = {}

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}

TGJU_SLUGS = {
    "dollar": "price_dollar_rl", "euro": "price_eur", "pound": "price_gbp",
    "dirham": "price_aed", "lira": "price_try", "yuan": "price_cny",
    "ruble": "price_rub", "afghani": "price_afn", "dinar_iq": "price_iqd",
    "gold18": "geram18", "silver": "silver_999", "copper": "copper",
    "coin_emami": "sekee", "coin_bahar": "sekeb", "coin_half": "nim",
    "coin_quarter": "rob",
}
_AJAX_URLS = ("https://call1.tgju.org/ajax.json", "https://call2.tgju.org/ajax.json")
_BULK_CACHE_KEY = "tgju_bulk"
_BULK_TTL = 90

SYMBOL_TO_ID = {
    "btc": "bitcoin", "bitcoin": "bitcoin", "بیتکوین": "bitcoin", "بیت‌کوین": "bitcoin",
    "eth": "ethereum", "ethereum": "ethereum", "اتریوم": "ethereum",
    "usdt": "tether", "tether": "tether", "تتر": "tether",
    "usdc": "usd-coin", "busd": "binance-usd", "ton": "the-open-network",
    "toncoin": "the-open-network", "تون": "the-open-network", "bnb": "binancecoin",
    "sol": "solana", "xrp": "ripple", "ada": "cardano", "doge": "dogecoin",
    "dot": "polkadot", "matic": "matic-network", "polygon": "matic-network",
    "avax": "avalanche-2", "link": "chainlink", "trx": "tron", "shib": "shiba-inu",
    "ltc": "litecoin", "bch": "bitcoin-cash", "atom": "cosmos", "uni": "uniswap",
    "near": "near", "apt": "aptos", "arb": "arbitrum", "op": "optimism", "fil": "filecoin",
    "icp": "internet-computer", "vet": "vechain", "algo": "algorand", "xlm": "stellar",
    "eos": "eos", "xtz": "tezos", "aave": "aave", "mkr": "maker",
    "comp": "compound-governance-token", "snx": "havven", "crv": "curve-dao-token",
    "sushi": "sushi", "1inch": "1inch", "pepe": "pepe", "floki": "floki",
    "bonk": "bonk", "wif": "dogwifcoin", "sui": "sui", "sei": "sei-network",
    "inj": "injective-protocol", "tia": "celestia", "render": "render-token",
    "fet": "fetch-ai", "rndr": "render-token", "imx": "immutable-x", "gala": "gala",
    "sand": "the-sandbox", "mana": "decentraland", "axs": "axie-infinity",
    "theta": "theta-token", "ftm": "fantom", "hbar": "hedera-hashgraph",
    "egld": "elrond-erd-2", "kas": "kaspa", "rune": "thorchain", "stx": "blockstack",
    "ordi": "ordinals", "sats": "sats-ordinals",
}

load_modular_part(__file__, 'finance_core_parts/part_001__get_usd_rial.py')

load_modular_part(__file__, 'finance_core_parts/part_002_pn.py')


load_modular_part(__file__, 'finance_core_parts/part_003__parse_price.py')


load_modular_part(__file__, 'finance_core_parts/part_004__fetch_tgju_bulk.py')


load_modular_part(__file__, 'finance_core_parts/part_005__tgju_price.py')



load_modular_part(__file__, 'finance_core_parts/part_006_resolve_coin_id.py')


load_modular_part(__file__, 'finance_core_parts/part_007__crypto_simple.py')


load_modular_part(__file__, 'finance_core_parts/part_008__top_from_coinlore.py')


load_modular_part(__file__, 'finance_core_parts/part_009__top_from_paprika.py')


load_modular_part(__file__, 'finance_core_parts/part_010_get_top_crypto.py')


load_modular_part(__file__, 'finance_core_parts/part_011_get_crypto_price.py')


load_modular_part(__file__, 'finance_core_parts/part_012_convert_crypto.py')


load_modular_part(__file__, 'finance_core_parts/part_013_full_market_prices.py')


load_modular_part(__file__, 'finance_core_parts/part_014_rial_toman.py')


# نام‌های رایج فارسی برای ارز و کریپتو
_FA_CURRENCY = {
    "دلار": "usd", "دلارآمریکا": "usd", "usd": "usd", "dollar": "usd", "دلاری": "usd",
    "یورو": "eur", "euro": "eur", "eur": "eur",
    "پوند": "gbp", "pound": "gbp", "gbp": "gbp",
    "تومان": "toman", "تومن": "toman", "tmn": "toman",
    "ریال": "rial", "irr": "rial",
    "درهم": "aed", "aed": "aed",
    "لیر": "try", "try": "try",
    "یوان": "cny", "cny": "cny",
    "روبل": "rub", "rub": "rub",
    "بیتکوین": "btc", "بیت‌کوین": "btc", "بیت کوین": "btc",
    "اتریوم": "eth", "تتر": "usdt", "تون": "ton", "سولانا": "sol",
    "کاردانو": "ada", "ریپل": "xrp", "دوج": "doge", "دوج‌کوین": "doge",
}


load_modular_part(__file__, 'finance_core_parts/part_015_convert_currency.py')


load_modular_part(__file__, 'finance_core_parts/part_016_profit_loss.py')


load_modular_part(__file__, 'finance_core_parts/part_017_parse_profit.py')


load_modular_part(__file__, 'finance_core_parts/part_018_parse_currency_input.py')

