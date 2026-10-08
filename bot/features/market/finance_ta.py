"""Technical-analysis helpers extracted from finance.py.

This module keeps market calculation code focused and reduces the size of the
market facade. It lazily references runtime HTTP/logging dependencies from
finance.py after that module is initialized.
"""
from __future__ import annotations
from bot.utils.modular_loader import load_modular_part
import asyncio
from bot.features.market import finance as _f
from bot.logger import logger
from bot.utils.http_client import pooled_async_client, request_with_retry, safe_json

# Compatibility aliases preserved from the original finance.py implementation.
# finance_ta is loaded through the finance facade after it is initialized.
_fetch_klines_interval = _f._fetch_klines_interval

load_modular_part(__file__, 'finance_ta_parts/part_001__fetch_klines_for_ta.py')


load_modular_part(__file__, 'finance_ta_parts/part_002__sma.py')


load_modular_part(__file__, 'finance_ta_parts/part_003__rsi.py')


load_modular_part(__file__, 'finance_ta_parts/part_004__adx_approx.py')


load_modular_part(__file__, 'finance_ta_parts/part_005__compute_ta.py')



load_modular_part(__file__, 'finance_ta_parts/part_006__atr.py')


load_modular_part(__file__, 'finance_ta_parts/part_007__detect_candle_patterns.py')


load_modular_part(__file__, 'finance_ta_parts/part_008__score_timeframe.py')


load_modular_part(__file__, 'finance_ta_parts/part_009__mtf_bundle.py')



load_modular_part(__file__, 'finance_ta_parts/part_010__market_structure.py')


load_modular_part(__file__, 'finance_ta_parts/part_011__rsi_divergence.py')


load_modular_part(__file__, 'finance_ta_parts/part_012__volume_breakout.py')


load_modular_part(__file__, 'finance_ta_parts/part_013__demand_supply_zone.py')



load_modular_part(__file__, 'finance_ta_parts/part_014__detect_chart_patterns.py')


load_modular_part(__file__, 'finance_ta_parts/part_015__price_action_analysis.py')

load_modular_part(__file__, 'finance_ta_parts/part_016__mtf_convergence.py')




load_modular_part(__file__, 'finance_ta_parts/part_017__advanced_levels.py')


load_modular_part(__file__, 'finance_ta_parts/part_018__market_regime.py')


load_modular_part(__file__, 'finance_ta_parts/part_019__professional_score.py')
