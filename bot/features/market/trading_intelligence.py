"""Advanced trading intelligence: backtesting, regime, risk, calibration and alerts.
Pure helpers are intentionally dependency-free so they can be unit-tested offline.
"""
from __future__ import annotations
from bot.utils.modular_loader import load_modular_part
import math
import time
from statistics import mean


load_modular_part(__file__, 'trading_intelligence_parts/part_001__clamp.py')


load_modular_part(__file__, 'trading_intelligence_parts/part_002_detect_regime.py')


load_modular_part(__file__, 'trading_intelligence_parts/part_003_dynamic_weights.py')


load_modular_part(__file__, 'trading_intelligence_parts/part_004_quality_gate.py')


load_modular_part(__file__, 'trading_intelligence_parts/part_005_risk_plan.py')


load_modular_part(__file__, 'trading_intelligence_parts/part_006__forward_return.py')


load_modular_part(__file__, 'trading_intelligence_parts/part_007_backtest_directional.py')


load_modular_part(__file__, 'trading_intelligence_parts/part_008_walk_forward.py')


load_modular_part(__file__, 'trading_intelligence_parts/part_009_calibration.py')


load_modular_part(__file__, 'trading_intelligence_parts/part_010_alert_flags.py')


load_modular_part(__file__, 'trading_intelligence_parts/part_011_dedupe_alerts.py')
