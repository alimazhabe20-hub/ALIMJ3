"""Crypto-analysis orchestration extracted from finance.py."""
from __future__ import annotations
from bot.utils.modular_loader import load_modular_part
import asyncio
from bot.features.market import finance as _f

# Runtime aliases; this module is imported lazily by the finance facade.
# Keep all dependencies that were originally module-level in finance.py exposed
# here after the V27 decomposition.  The facade is fully initialized before
# finance_crypto is imported, so these aliases avoid circular imports while
# preserving the original analysis pipeline.

SYMBOL_TO_ID = _f.SYMBOL_TO_ID
resolve_coin_id = _f.resolve_coin_id
pooled_async_client = _f.pooled_async_client
request_with_retry = _f.request_with_retry
safe_json = _f.safe_json
_fetch_coingecko_detail = _f._fetch_coingecko_detail
_fetch_binance_futures = _f._fetch_binance_futures
_fetch_klines_interval = _f._fetch_klines_interval
_atr = _f._atr
_detect_candle_patterns = _f._detect_candle_patterns
_format_fear_greed = getattr(_f, "_format_fear_greed", None)
get_crypto_analysis_short = getattr(_f, "get_crypto_analysis_short", None)
_fetch_klines_for_ta = _f._fetch_klines_for_ta
_compute_ta = _f._compute_ta
_support_resistance = _f._support_resistance
_derive_signal = _f._derive_signal
_mtf_bundle = _f._mtf_bundle
_market_structure = _f._market_structure
_rsi_divergence = _f._rsi_divergence
_volume_breakout = _f._volume_breakout
_demand_supply_zone = _f._demand_supply_zone
_mtf_convergence = _f._mtf_convergence
_advanced_levels = _f._advanced_levels
_price_action_analysis = _f._price_action_analysis
_market_regime = _f._market_regime
_professional_score = _f._professional_score
from bot.features.market.trading_intelligence import (backtest_directional, walk_forward, calibration, alert_flags, risk_plan, dedupe_alerts)
from bot.features.market.trading_adaptation import settle_signals, record_signal, adaptive_profile, performance_summary
_fetch_fundamentals = _f._fetch_fundamentals
_build_smart_summary = _f._build_smart_summary
_default_guide = _f._default_guide
_build_smart_summary_pair = _f._build_smart_summary_pair
_scenarios = _f._scenarios
_signal_track_stub = _f._signal_track_stub
_pair_from_symbol = _f._pair_from_symbol
_format_long_short = _f._format_long_short
_fetch_fear_greed = _f._fetch_fear_greed
_fetch_orderflow_context = getattr(_f, "_fetch_orderflow_context", None)
_tgju_price = getattr(_f, "_tgju_price", None)
_request_with_retry = _f.request_with_retry
safe_json = _f.safe_json
logger = _f.logger

# Shared formatter: both crypto and gold reports use it. Keeping it at module
# scope prevents NameError when analyze_crypto renders support/resistance.
load_modular_part(__file__, 'finance_crypto_parts/part_001_fmt_p.py')

if _format_fear_greed is None:
    def _format_fear_greed(data):
        return str(data or "")

load_modular_part(__file__, 'finance_crypto_parts/part_002_analyze_gold.py')


load_modular_part(__file__, 'finance_crypto_parts/part_003__empty_async.py')

load_modular_part(__file__, 'finance_crypto_parts/part_004_analyze_crypto.py')


load_modular_part(__file__, 'finance_crypto_parts/part_005__default_guide.py')


load_modular_part(__file__, 'finance_crypto_parts/part_006__build_smart_summary_pair.py')


load_modular_part(__file__, 'finance_crypto_parts/part_007__fetch_fundamentals.py')



load_modular_part(__file__, 'finance_crypto_parts/part_008_get_gold_chart.py')

load_modular_part(__file__, 'finance_crypto_parts/part_009__build_smart_summary.py')

