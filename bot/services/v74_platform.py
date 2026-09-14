"""V74 Reliability & Intelligence Core.

Twelve bounded production subsystems are implemented here:
1) Agent 2.0, 2) Tool System 2.0, 3) Security 2.0, 4) Self-Healing 2.0,
5) Performance 2.0, 6) QA 2.0, 7) Observability, 8) Web Intelligence 2.0,
9) RAG 2.0, 10) Persistence 2.0, 11) Provider Reliability, 12) Runtime/API Reliability.

Design rules: bounded work, fail closed, no secret exposure, no destructive autonomous
actions, deterministic fallbacks, and compatibility with the existing V70-V73 stack.
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
import sqlite3
import time
import urllib.parse
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

from bot.logger import logger

VERSION = "74.0.0"
MAX_AGENT_STEPS = max(1, min(10, int(os.getenv("V74_AGENT_MAX_STEPS", "6"))))
MAX_AGENT_CALLS = max(2, min(24, int(os.getenv("V74_AGENT_MAX_CALLS", "12"))))
MAX_AGENT_REPAIRS = max(0, min(3, int(os.getenv("V74_AGENT_MAX_REPAIRS", "2"))))
AGENT_BUDGET_MS = max(5000, min(120000, int(os.getenv("V74_AGENT_BUDGET_MS", "45000"))))
TOOL_RETRIES = max(0, min(3, int(os.getenv("V74_TOOL_RETRIES", "1"))))
CACHE_TTL = max(2, int(os.getenv("V74_CACHE_TTL", "20")))
CACHE_MAX = max(64, int(os.getenv("V74_CACHE_MAX", "2048")))

# ---------------------------------------------------------------------------
# 3) Security 2.0
# ---------------------------------------------------------------------------
_SECRET_PATTERNS = (
    re.compile(r"(?i)(bot[_-]?token|api[_-]?key|secret|password|authorization|cookie)\s*[:=]\s*([^\s,;]+)"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)(sk-[A-Za-z0-9_-]{12,}|AIza[0-9A-Za-z_-]{20,})"),
)
_PROMPT_INJECTION_PATTERNS = (
    r"ignore\s+(?:(?:all|any)\s+)?(?:previous|prior)\s+instructions",
    r"نادیده\s+بگیر\s+(همه|تمام|دستورهای|دستورات)",
    r"دستورهای\s+سیستم\s+را\s+نادیده",
    r"system\s+prompt|developer\s+message",
    r"reveal\s+(the\s+)?(system|developer)\s+prompt",
    r"افشای?\s+(پرامپت|دستور)\s+(سیستم|سازنده)",
)


load_modular_part(__file__, 'v74_platform_parts/part_001_redact_secrets.py')


load_modular_part(__file__, 'v74_platform_parts/part_002_detect_prompt_injection.py')


load_modular_part(__file__, 'v74_platform_parts/part_003_safe_public_url.py')


load_modular_part(__file__, 'v74_platform_parts/part_004_safe_archive_member.py')


load_modular_part(__file__, 'v74_platform_parts/part_005_safe_path.py')


load_modular_part(__file__, 'v74_platform_parts/part_006_sanitize_untrusted_text.py')

# ---------------------------------------------------------------------------
# 2) Tool System 2.0
# ---------------------------------------------------------------------------
load_modular_part(__file__, 'v74_platform_parts/part_007_ToolPolicy.py')

_TOOL_POLICIES: dict[str, ToolPolicy] = {}
_TOOL_FAILURES: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=30))
_TOOL_DISABLED_UNTIL: dict[str, float] = {}


load_modular_part(__file__, 'v74_platform_parts/part_008_register_tool_policy.py')


load_modular_part(__file__, 'v74_platform_parts/part_009_tool_policy_snapshot.py')


load_modular_part(__file__, 'v74_platform_parts/part_010_tool_allowed.py')


load_modular_part(__file__, 'v74_platform_parts/part_011_note_tool_failure.py')


load_modular_part(__file__, 'v74_platform_parts/part_012_recover_tool.py')

# ---------------------------------------------------------------------------
# 1) Agent 2.0
# ---------------------------------------------------------------------------
load_modular_part(__file__, 'v74_platform_parts/part_013_AgentStep.py')


load_modular_part(__file__, 'v74_platform_parts/part_014__agent_intents.py')


load_modular_part(__file__, 'v74_platform_parts/part_015__should_stop.py')


load_modular_part(__file__, 'v74_platform_parts/part_016_run_agent_2.py')

# ---------------------------------------------------------------------------
# 5) Performance 2.0
# ---------------------------------------------------------------------------
_CACHE: dict[str, tuple[float, Any]] = {}
_INFLIGHT: dict[str, asyncio.Task] = {}
_PERF: dict[str, dict[str, float]] = defaultdict(lambda: {"calls": 0, "errors": 0, "total_ms": 0.0, "max_ms": 0.0})
_SLOW: Counter[str] = Counter()


load_modular_part(__file__, 'v74_platform_parts/part_017_cache_get.py')


load_modular_part(__file__, 'v74_platform_parts/part_018_cache_set.py')


load_modular_part(__file__, 'v74_platform_parts/part_019_clear_performance_cache.py')


load_modular_part(__file__, 'v74_platform_parts/part_020_record_performance.py')


load_modular_part(__file__, 'v74_platform_parts/part_021_performance_snapshot.py')

# ---------------------------------------------------------------------------
# 4) Self-Healing 2.0
# ---------------------------------------------------------------------------
_FAILURES: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=50))
_RECOVERY_LOG: deque[dict[str, Any]] = deque(maxlen=100)


load_modular_part(__file__, 'v74_platform_parts/part_022_note_failure.py')


load_modular_part(__file__, 'v74_platform_parts/part_023_recover_component.py')


load_modular_part(__file__, 'v74_platform_parts/part_024_healing_snapshot.py')

# ---------------------------------------------------------------------------
# 8) Web Intelligence 2.0
# ---------------------------------------------------------------------------
_SOURCE_WEIGHTS = {"wikipedia.org": .75, "reuters.com": .95, "bbc.com": .90, "gov": .98, "edu": .95}


load_modular_part(__file__, 'v74_platform_parts/part_025_source_score.py')


load_modular_part(__file__, 'v74_platform_parts/part_026_dedupe_sources.py')


load_modular_part(__file__, 'v74_platform_parts/part_027_verify_claims.py')

# ---------------------------------------------------------------------------
# 9) RAG 2.0
# ---------------------------------------------------------------------------
_STOP = set("the and for with that this from are was is به برای و از که این آن را در با است یک های هایو".split())


load_modular_part(__file__, 'v74_platform_parts/part_028_rag_tokens.py')


load_modular_part(__file__, 'v74_platform_parts/part_029_chunk_document.py')


load_modular_part(__file__, 'v74_platform_parts/part_030_rag_rank.py')


load_modular_part(__file__, 'v74_platform_parts/part_031_rag_context.py')

# ---------------------------------------------------------------------------
# 10) Persistence 2.0
# ---------------------------------------------------------------------------
load_modular_part(__file__, 'v74_platform_parts/part_032_db_integrity.py')


load_modular_part(__file__, 'v74_platform_parts/part_033_verify_backup.py')


load_modular_part(__file__, 'v74_platform_parts/part_034_persistence_snapshot.py')

# ---------------------------------------------------------------------------
# 11) Provider Reliability + 12) Runtime/API Reliability
# ---------------------------------------------------------------------------
_PROVIDER: dict[str, dict[str, Any]] = defaultdict(lambda: {"calls":0,"errors":0,"total_ms":0.0,"cooldown_until":0.0})
_RUNTIME: dict[str, Any] = {"started_at": time.time(), "readiness": {}, "last_errors": deque(maxlen=50)}


load_modular_part(__file__, 'v74_platform_parts/part_035_provider_event.py')


load_modular_part(__file__, 'v74_platform_parts/part_036_provider_available.py')


load_modular_part(__file__, 'v74_platform_parts/part_037_provider_snapshot.py')


load_modular_part(__file__, 'v74_platform_parts/part_038_set_readiness.py')


load_modular_part(__file__, 'v74_platform_parts/part_039_runtime_snapshot.py')

# ---------------------------------------------------------------------------
# 6) QA 2.0
# ---------------------------------------------------------------------------
load_modular_part(__file__, 'v74_platform_parts/part_040_qa_snapshot.py')

# ---------------------------------------------------------------------------
# 7) Observability
# ---------------------------------------------------------------------------
load_modular_part(__file__, 'v74_platform_parts/part_041_observability_snapshot.py')


load_modular_part(__file__, 'v74_platform_parts/part_042_admin_dashboard_data.py')

# ---------------------------------------------------------------------------
# Database tables + self-test
# ---------------------------------------------------------------------------
load_modular_part(__file__, 'v74_platform_parts/part_043_init_v74_tables.py')


load_modular_part(__file__, 'v74_platform_parts/part_044_self_test.py')
