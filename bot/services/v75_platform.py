"""ALIMJ3 V75 — Intelligence & Automation Platform.

Adds the requested 17 capability groups as bounded, production-safe primitives:
Agent 3.0, Multi-Agent, Admin Dashboard data, Security Center, Web Intelligence
3.0, RAG 3.0, Market Intelligence 2.0, News Intelligence, Economic Calendar 2.0,
Backup/DR 3.0, Performance 3.0, QA 3.0, Workflow Builder, Smart Alerts,
Memory 2.0, Workspace, and Report Generator.

The module is intentionally dependency-light. Network/AI-heavy operations delegate
to existing project services and degrade safely when an optional provider is absent.
"""
from __future__ import annotations
from bot.utils.modular_loader import load_modular_part

import ast
import csv
import hashlib
import io
import json
import os
import re
import sqlite3
import time
import uuid
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

from bot.logger import logger

VERSION = "75.0.0"
MAX_WORKFLOW_STEPS = max(1, min(12, int(os.getenv("V75_WORKFLOW_MAX_STEPS", "8"))))
MAX_AGENT_STEPS = max(1, min(12, int(os.getenv("V75_AGENT_MAX_STEPS", "8"))))
MAX_AGENT_CALLS = max(2, min(32, int(os.getenv("V75_AGENT_MAX_CALLS", "16"))))
MAX_AGENT_MS = max(5000, min(180000, int(os.getenv("V75_AGENT_BUDGET_MS", "60000"))))
MAX_ALERTS_PER_USER = max(10, min(500, int(os.getenv("V75_MAX_ALERTS", "100"))))
MAX_MEMORY_ITEMS = max(20, min(2000, int(os.getenv("V75_MAX_MEMORY", "500"))))

# ---------------------------------------------------------------------------
# Generic helpers / security
# ---------------------------------------------------------------------------
_SECRET_RE = re.compile(r"(?i)(bot[_-]?token|api[_-]?key|secret|password|authorization|cookie)\s*[:=]\s*([^\s,;]+)")
_INJECTION_RE = re.compile(
    r"(?i)(ignore\s+(all|any|previous|prior)\s+instructions|system\s+prompt|developer\s+message|reveal\s+.*prompt|نادیده\s+بگیر|دستورهای?\s+سیستم)"
)

load_modular_part(__file__, 'v75_platform_parts/part_001_redact.py')


load_modular_part(__file__, 'v75_platform_parts/part_002_security_scan.py')


load_modular_part(__file__, 'v75_platform_parts/part_003_stable_hash.py')

# ---------------------------------------------------------------------------
# SQLite persistence
# ---------------------------------------------------------------------------
load_modular_part(__file__, 'v75_platform_parts/part_004__db.py')


load_modular_part(__file__, 'v75_platform_parts/part_005_init_v75_tables.py')

# ---------------------------------------------------------------------------
# 1/2 Agent 3.0 + Multi-Agent
# ---------------------------------------------------------------------------
load_modular_part(__file__, 'v75_platform_parts/part_006_AgentTask.py')


load_modular_part(__file__, 'v75_platform_parts/part_007_plan_agent.py')


load_modular_part(__file__, 'v75_platform_parts/part_008_run_agent_3.py')


load_modular_part(__file__, 'v75_platform_parts/part_009_run_multi_agent.py')


load_modular_part(__file__, 'v75_platform_parts/part_010__specialist_for.py')

# ---------------------------------------------------------------------------
# 3 Security Center
# ---------------------------------------------------------------------------
load_modular_part(__file__, 'v75_platform_parts/part_011_security_center_snapshot.py')

# ---------------------------------------------------------------------------
# 5 Web Intelligence 3.0 / 6 RAG 3.0
# ---------------------------------------------------------------------------
load_modular_part(__file__, 'v75_platform_parts/part_012_rank_sources.py')


load_modular_part(__file__, 'v75_platform_parts/part_013_rag_chunk.py')


load_modular_part(__file__, 'v75_platform_parts/part_014_rag_rank.py')

# ---------------------------------------------------------------------------
# 7 Market Intelligence 2.0
# ---------------------------------------------------------------------------
load_modular_part(__file__, 'v75_platform_parts/part_015_market_intelligence_2.py')

# ---------------------------------------------------------------------------
# 8 News / 9 Calendar intelligence
# ---------------------------------------------------------------------------
load_modular_part(__file__, 'v75_platform_parts/part_016_score_news.py')


load_modular_part(__file__, 'v75_platform_parts/part_017_economic_surprise.py')

# ---------------------------------------------------------------------------
# 10 Backup / DR 3.0
# ---------------------------------------------------------------------------
load_modular_part(__file__, 'v75_platform_parts/part_018_backup_integrity.py')

# ---------------------------------------------------------------------------
# 11 Performance / 12 QA
# ---------------------------------------------------------------------------
_PERF=defaultdict(lambda: deque(maxlen=100))

load_modular_part(__file__, 'v75_platform_parts/part_019_record_perf.py')


load_modular_part(__file__, 'v75_platform_parts/part_020_performance_snapshot.py')


load_modular_part(__file__, 'v75_platform_parts/part_021_qa_snapshot.py')

# ---------------------------------------------------------------------------
# 13 Workflow Builder
# ---------------------------------------------------------------------------
load_modular_part(__file__, 'v75_platform_parts/part_022_validate_workflow.py')


load_modular_part(__file__, 'v75_platform_parts/part_023_execute_workflow.py')

# ---------------------------------------------------------------------------
# 14 Smart Alerts
# ---------------------------------------------------------------------------
load_modular_part(__file__, 'v75_platform_parts/part_024_create_alert.py')


load_modular_part(__file__, 'v75_platform_parts/part_025_evaluate_alert.py')

# ---------------------------------------------------------------------------
# 15 Memory 2.0 / 16 Workspace
# ---------------------------------------------------------------------------
load_modular_part(__file__, 'v75_platform_parts/part_026_remember.py')


load_modular_part(__file__, 'v75_platform_parts/part_027_recall.py')


load_modular_part(__file__, 'v75_platform_parts/part_028_create_workspace.py')

# ---------------------------------------------------------------------------
# 17 Report Generator
# ---------------------------------------------------------------------------
load_modular_part(__file__, 'v75_platform_parts/part_029_generate_report.py')

# ---------------------------------------------------------------------------
# Dashboard + self test
# ---------------------------------------------------------------------------
load_modular_part(__file__, 'v75_platform_parts/part_030_dashboard.py')


load_modular_part(__file__, 'v75_platform_parts/part_031_self_test.py')
