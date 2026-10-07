"""V71 production hardening and AI platform services.
No automatic conversation summarisation is implemented here.
"""
from __future__ import annotations
from bot.utils.modular_loader import load_modular_part

import ast
import asyncio
import hashlib
import ipaddress
import os
import re
import socket
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from bot.database_core import get_db_connection, _execute_write
from bot.logger import logger

SUPPORTED_LANGS = ("fa", "en", "ar")


load_modular_part(__file__, 'v71_platform_parts/part_001_init_v71_tables.py')


load_modular_part(__file__, 'v71_platform_parts/part_002_set_workspace.py')


load_modular_part(__file__, 'v71_platform_parts/part_003_get_workspace.py')


load_modular_part(__file__, 'v71_platform_parts/part_004_save_branch.py')


load_modular_part(__file__, 'v71_platform_parts/part_005_list_branches.py')


load_modular_part(__file__, 'v71_platform_parts/part_006_schedule_ai.py')


load_modular_part(__file__, 'v71_platform_parts/part_007_due_ai_jobs.py')


load_modular_part(__file__, 'v71_platform_parts/part_008_complete_ai_job.py')


load_modular_part(__file__, 'v71_platform_parts/part_009_notification_claim.py')


load_modular_part(__file__, 'v71_platform_parts/part_010_detect_language.py')


load_modular_part(__file__, 'v71_platform_parts/part_011_personalize.py')


load_modular_part(__file__, 'v71_platform_parts/part_012_code_agent_review.py')


load_modular_part(__file__, 'v71_platform_parts/part_013_verify_facts_with_sources.py')


load_modular_part(__file__, 'v71_platform_parts/part_014_source_intelligence.py')


load_modular_part(__file__, 'v71_platform_parts/part_015_security_check_url.py')


load_modular_part(__file__, 'v71_platform_parts/part_016_ai_route_hint.py')


load_modular_part(__file__, 'v71_platform_parts/part_017_auto_recovery_policy.py')


load_modular_part(__file__, 'v71_platform_parts/part_018_run_self_test_suite.py')


load_modular_part(__file__, 'v71_platform_parts/part_019_health_snapshot.py')


load_modular_part(__file__, 'v71_platform_parts/part_020_self_test.py')
