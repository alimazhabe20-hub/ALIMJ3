"""Persistent adaptive intelligence for the market-analysis engine.

This module learns only from recorded, settled signals. It never fabricates
outcomes and keeps an auditable JSON ledger with bounded size.
"""
from __future__ import annotations
from bot.utils.modular_loader import load_modular_part
import json, os, time, uuid, math, copy
from collections import defaultdict
from statistics import mean

_DEFAULT = {"version": 1, "signals": [], "weights": {}, "stats": {}}


load_modular_part(__file__, 'trading_adaptation_parts/part_001__path.py')


load_modular_part(__file__, 'trading_adaptation_parts/part_002__load.py')


load_modular_part(__file__, 'trading_adaptation_parts/part_003__save.py')


load_modular_part(__file__, 'trading_adaptation_parts/part_004_record_signal.py')


load_modular_part(__file__, 'trading_adaptation_parts/part_005_settle_signals.py')


load_modular_part(__file__, 'trading_adaptation_parts/part_006__rebuild_stats.py')


load_modular_part(__file__, 'trading_adaptation_parts/part_007_adaptive_profile.py')


load_modular_part(__file__, 'trading_adaptation_parts/part_008_adaptive_weights.py')


load_modular_part(__file__, 'trading_adaptation_parts/part_009_adapt_score.py')


load_modular_part(__file__, 'trading_adaptation_parts/part_010_kill_switch.py')


load_modular_part(__file__, 'trading_adaptation_parts/part_011_performance_summary.py')


load_modular_part(__file__, 'trading_adaptation_parts/part_012__max_dd.py')
