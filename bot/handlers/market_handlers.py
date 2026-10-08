"""Stable public facade.

IMPORTANT: Keep this file small and stable. New functionality belongs in the
secondary ``market_handlers_parts/`` modules. The complete legacy implementation is kept
unchanged in ``market_handlers_parts/part_999_core_legacy.py`` for compatibility.
"""
from bot.utils.modular_loader import load_modular_part

load_modular_part(__file__, 'market_handlers_parts/part_999_core_legacy.py')


_legacy_h_profit = _h_profit
_legacy_h_currency = _h_currency
_legacy_h_crypto_full = _h_crypto_full
_legacy_h_crypto_pos = _h_crypto_pos
_legacy_h_crypto_chart = _h_crypto_chart
_legacy_h_crypto_analyze = _h_crypto_analyze
async def _h_profit(*args, **kwargs): return await _legacy_h_profit(*args, **kwargs)
async def _h_currency(*args, **kwargs): return await _legacy_h_currency(*args, **kwargs)
async def _h_crypto_full(*args, **kwargs): return await _legacy_h_crypto_full(*args, **kwargs)
async def _h_crypto_pos(*args, **kwargs): return await _legacy_h_crypto_pos(*args, **kwargs)
async def _h_crypto_chart(*args, **kwargs): return await _legacy_h_crypto_chart(*args, **kwargs)
async def _h_crypto_analyze(*args, **kwargs): return await _legacy_h_crypto_analyze(*args, **kwargs)
