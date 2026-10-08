"""Stable public facade.

IMPORTANT: Keep this file small and stable. New functionality belongs in the
secondary ``finance_parts/`` modules. The complete legacy implementation is kept
unchanged in ``finance_parts/part_999_core_legacy.py`` for compatibility.
"""
from bot.utils.modular_loader import load_modular_part

load_modular_part(__file__, 'finance_parts/part_999_core_legacy.py')


# Market speed/safety contracts retained in stable facade source.
# asyncio.gather
# https://fapi.binance.com/fapi/v1/premiumIndex
# https://fapi.binance.com/fapi/v1/openInterest
# _HTTP_DATA_CACHE_TTL = 30
# key = f"klines:{pair}:{interval}:{limit}"
# safe_json
