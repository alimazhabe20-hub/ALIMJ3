"""ALIMJ3 Update Center.

Safe, read-only release discovery. The bot never replaces its own files from a
remote URL automatically. An operator publishes a small JSON manifest at
UPDATE_MANIFEST_URL; Update Center validates it, compares semantic versions,
checks local runtime/dependencies/schema, caches the result, and reports a
clear green/yellow/red status.
"""
from __future__ import annotations
from bot.utils.modular_loader import load_modular_part

import hashlib
import importlib.util
import json
import os
import platform
import re
import sqlite3
import time
import ipaddress
import socket
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from bot.config import config
from bot.logger import logger
from bot.release import APP_NAME, RELEASE_CHANNEL, VERSION
from bot.database import DB_PATH

CACHE_TTL = max(60, int(os.getenv("UPDATE_CHECK_TTL", "1800")))
TIMEOUT = max(3.0, min(30.0, float(os.getenv("UPDATE_CHECK_TIMEOUT", "10"))))
MAX_MANIFEST_BYTES = 512 * 1024
_VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$")


load_modular_part(__file__, 'update_center_parts/part_001__version_tuple.py')


load_modular_part(__file__, 'update_center_parts/part_002__is_public_ip.py')


load_modular_part(__file__, 'update_center_parts/part_003__valid_manifest_url.py')


load_modular_part(__file__, 'update_center_parts/part_004__manifest_url.py')


load_modular_part(__file__, 'update_center_parts/part_005__cache_path.py')


load_modular_part(__file__, 'update_center_parts/part_006__load_cache.py')


load_modular_part(__file__, 'update_center_parts/part_007__save_cache.py')


load_modular_part(__file__, 'update_center_parts/part_008__read_manifest.py')


load_modular_part(__file__, 'update_center_parts/part_009__dependency_check.py')


load_modular_part(__file__, 'update_center_parts/part_010__schema_check.py')


load_modular_part(__file__, 'update_center_parts/part_011__local_checks.py')


load_modular_part(__file__, 'update_center_parts/part_012__status_for.py')


load_modular_part(__file__, 'update_center_parts/part_013__safe_manifest_view.py')


load_modular_part(__file__, 'update_center_parts/part_014_check_for_updates.py')


load_modular_part(__file__, 'update_center_parts/part_015_update_summary.py')


load_modular_part(__file__, 'update_center_parts/part_016_maybe_notify_admins.py')


load_modular_part(__file__, 'update_center_parts/part_017_self_test.py')
