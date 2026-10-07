"""Professional ICT (Inner Circle Trader) analysis engine.

Concepts covered (educational implementation):
  - Swing points (strength-weighted fractals)
  - External market structure: HH/HL/LH/LL, BOS, MSS/CHoCH
  - Internal structure (shorter swing length)
  - Fair Value Gaps + CE (50%) + partial fill state
  - Order Blocks, Breaker Blocks, mitigation status
  - Liquidity: BSL/SSL, equal highs/lows, sweeps / stop-runs
  - Dealing range → Premium / Discount / Equilibrium + OTE (0.62–0.79)
  - Displacement (impulse) quality vs ATR
  - Session killzones (UTC)
  - Multi-timeframe bias blend when higher TF data is available
  - Confidence-weighted directional bias

Not financial advice.
"""
from __future__ import annotations
from bot.utils.modular_loader import load_modular_part

from datetime import datetime, timezone
from typing import Any

from bot.logger import logger


# ── utils ──────────────────────────────────────────────────────────────────

load_modular_part(__file__, 'finance_ict_parts/part_001__f.py')


load_modular_part(__file__, 'finance_ict_parts/part_002__pct.py')


load_modular_part(__file__, 'finance_ict_parts/part_003__atr.py')


load_modular_part(__file__, 'finance_ict_parts/part_004__body.py')


load_modular_part(__file__, 'finance_ict_parts/part_005__range.py')


# ── swings ─────────────────────────────────────────────────────────────────

load_modular_part(__file__, 'finance_ict_parts/part_006__swings.py')


load_modular_part(__file__, 'finance_ict_parts/part_007__swing_strength.py')


# ── market structure ───────────────────────────────────────────────────────

load_modular_part(__file__, 'finance_ict_parts/part_008__structure_from_swings.py')


# ── FVG ────────────────────────────────────────────────────────────────────

load_modular_part(__file__, 'finance_ict_parts/part_009__fair_value_gaps.py')


# ── Order blocks / breakers ────────────────────────────────────────────────

load_modular_part(__file__, 'finance_ict_parts/part_010__order_blocks.py')


# ── liquidity ──────────────────────────────────────────────────────────────

load_modular_part(__file__, 'finance_ict_parts/part_011__liquidity.py')


# ── dealing range / premium-discount / OTE ─────────────────────────────────

load_modular_part(__file__, 'finance_ict_parts/part_012__dealing_range.py')


# ── displacement ───────────────────────────────────────────────────────────

load_modular_part(__file__, 'finance_ict_parts/part_013__displacement.py')


# ── killzones ──────────────────────────────────────────────────────────────

load_modular_part(__file__, 'finance_ict_parts/part_014__killzone.py')


# ── bias engine ────────────────────────────────────────────────────────────

load_modular_part(__file__, 'finance_ict_parts/part_015__compute_bias.py')


# ── scenario notes ─────────────────────────────────────────────────────────

load_modular_part(__file__, 'finance_ict_parts/part_016__scenarios.py')


# ── core ───────────────────────────────────────────────────────────────────

load_modular_part(__file__, 'finance_ict_parts/part_017_analyze_ict_from_ohlc.py')


load_modular_part(__file__, 'finance_ict_parts/part_018_format_ict_report.py')


load_modular_part(__file__, 'finance_ict_parts/part_019_analyze_ict.py')
