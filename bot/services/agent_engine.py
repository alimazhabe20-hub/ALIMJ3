"""Bounded autonomous planning and self-repair for Rooze Ziba.

This layer deliberately uses deterministic intent planning rather than an
unbounded LLM loop. It selects existing read-only tools, executes at most a
small number of steps, and can retry a failed step with a safe fallback.
"""
from __future__ import annotations
from bot.utils.modular_loader import load_modular_part

import re
from typing import Any

from bot.logger import logger

MAX_PLAN_STEPS = 4
import os

MAX_REPAIRS = max(0, min(2, int(os.getenv("AI_AGENT_MAX_REPAIRS", "1"))))


load_modular_part(__file__, 'agent_engine_parts/part_001__current.py')


load_modular_part(__file__, 'agent_engine_parts/part_002__city_from_query.py')

load_modular_part(__file__, 'agent_engine_parts/part_003_build_plan.py')


load_modular_part(__file__, 'agent_engine_parts/part_004_run_agent.py')
