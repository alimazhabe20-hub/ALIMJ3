"""V73 platform: production agent architecture, security, self-healing, QA and performance.

All controls are bounded and deterministic. No unbounded autonomous loops, no secret
exposure, and no security bypasses are implemented here.
"""
from __future__ import annotations
from bot.utils.modular_loader import load_modular_part

import ast
import asyncio
import hashlib
import ipaddress
import json
import os
import re
import socket
import time
import urllib.parse
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from bot.logger import logger

VERSION = "73.0.0"
MAX_AGENT_STEPS = max(1, min(8, int(os.getenv("V73_AGENT_MAX_STEPS", "6"))))
MAX_AGENT_REPAIRS = max(0, min(3, int(os.getenv("V73_AGENT_MAX_REPAIRS", "2"))))
MAX_TOOL_CALLS_PER_RUN = max(2, min(20, int(os.getenv("V73_AGENT_MAX_TOOL_CALLS", "10"))))
SLOW_TOOL_MS = max(100, float(os.getenv("V73_SLOW_TOOL_MS", "3000")))

# ---------------------------------------------------------------------------
# Security primitives
# ---------------------------------------------------------------------------
_SECRET_PATTERNS = [
    re.compile(r"(?i)(bot[_-]?token|api[_-]?key|secret|password|authorization)\s*[:=]\s*([^\s,;]+)"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{12,}"),
]


load_modular_part(__file__, 'v73_platform_parts/part_001_redact_secrets.py')


load_modular_part(__file__, 'v73_platform_parts/part_002_safe_public_url.py')


load_modular_part(__file__, 'v73_platform_parts/part_003_safe_path.py')


load_modular_part(__file__, 'v73_platform_parts/part_004_safe_archive_member.py')


load_modular_part(__file__, 'v73_platform_parts/part_005_sanitize_tool_arguments.py')


# ---------------------------------------------------------------------------
# Agent architecture
# ---------------------------------------------------------------------------
load_modular_part(__file__, 'v73_platform_parts/part_006_AgentRun.py')


load_modular_part(__file__, 'v73_platform_parts/part_007__intent_candidates.py')


load_modular_part(__file__, 'v73_platform_parts/part_008_run_production_agent.py')


# ---------------------------------------------------------------------------
# Self-healing and circuit protection
# ---------------------------------------------------------------------------
_FAILURES: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=20))
_COOLDOWN_UNTIL: dict[str, float] = {}


load_modular_part(__file__, 'v73_platform_parts/part_009_note_failure.py')


load_modular_part(__file__, 'v73_platform_parts/part_010_component_available.py')


load_modular_part(__file__, 'v73_platform_parts/part_011_recover_component.py')


load_modular_part(__file__, 'v73_platform_parts/part_012_health_snapshot.py')


# ---------------------------------------------------------------------------
# Performance + QA
# ---------------------------------------------------------------------------
_PERF: dict[str, dict[str, float]] = defaultdict(lambda: {"calls": 0, "errors": 0, "total_ms": 0.0, "max_ms": 0.0})


load_modular_part(__file__, 'v73_platform_parts/part_013_record_performance.py')


load_modular_part(__file__, 'v73_platform_parts/part_014_performance_snapshot.py')


load_modular_part(__file__, 'v73_platform_parts/part_015_qa_snapshot.py')


load_modular_part(__file__, 'v73_platform_parts/part_016_init_v73_tables.py')
