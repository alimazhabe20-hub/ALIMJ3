"""Shared imports and module state for the refactored database."""

import sqlite3

import os

import time

from datetime import datetime

from typing import Any

from pathlib import Path

from bot.logger import logger

from bot.config import config

from bot.database_migrations import ensure_schema_version, schema_status, SCHEMA_VERSION

from bot.database_core import (
    BACKUP_KEEP, DB_BUSY_RETRIES, DB_BUSY_BACKOFF,
    _ensure_parent, get_db_connection, run_db_transaction, _execute_write,
    _user_count, restore_from_backup_if_needed, backup_db,
)

DB_PATH = config.DB_PATH

BACKUP_DIR = Path(config.BACKUP_DIR)

from typing import Any

from typing import Any

from typing import Any
