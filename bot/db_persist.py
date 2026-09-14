# -*- coding: utf-8 -*-
"""
بکاپ و ریستور خودکار و رایگان
  1) GitHub (GITHUB_TOKEN + GITHUB_REPO) → کاملاً خودکار
  2) تلگرام ادمین (دستی /backup و /restore)
"""
from bot.utils.modular_loader import load_modular_part
import asyncio
import base64
import os
import shutil
import sqlite3
import secrets
import gzip
import time
import re
import uuid
from datetime import datetime
from pathlib import Path

import requests

from bot.config import config
from bot.database import DB_PATH, backup_db, _user_count, get_db_connection
from bot.database_migrations import SCHEMA_VERSION
from bot.logger import logger

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
GITHUB_REPO = os.getenv("GITHUB_REPO", "").strip()  # مثال: username/bot-data-backup
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main").strip()
GITHUB_FILE = os.getenv("GITHUB_DB_FILE", "backups/latest.db.gz").strip().lstrip("/")
API = "https://api.github.com"
GITHUB_RETRIES = max(1, int(os.getenv("GITHUB_BACKUP_RETRIES", "4")))
GITHUB_BACKOFF = max(0.5, float(os.getenv("GITHUB_BACKUP_BACKOFF", "1.5")))
REMOTE_BACKUP_TIMEOUT = max(2.0, float(os.getenv("BACKUP_REMOTE_TIMEOUT", "8")))



# Telegram private channel backup (off-site, no card / external cloud required)
TELEGRAM_BACKUP_CHAT_ID = os.getenv("TELEGRAM_BACKUP_CHAT_ID", "").strip()
TELEGRAM_BACKUP_MAX_DOWNLOAD_BYTES = max(1, int(os.getenv("TELEGRAM_BACKUP_MAX_DOWNLOAD_MB", "20"))) * 1024 * 1024

load_modular_part(__file__, 'db_persist_parts/part_001__telegram_backup_chat_ids.py')

load_modular_part(__file__, 'db_persist_parts/part_002_telegram_backup_enabled.py')

load_modular_part(__file__, 'db_persist_parts/part_003__telegram_api.py')

load_modular_part(__file__, 'db_persist_parts/part_004__telegram_get.py')

load_modular_part(__file__, 'db_persist_parts/part_005_telegram_upload_db.py')


load_modular_part(__file__, 'db_persist_parts/part_006_telegram_download_pinned_db.py')

load_modular_part(__file__, 'db_persist_parts/part_007__gh_headers.py')


load_modular_part(__file__, 'db_persist_parts/part_008__validate_sqlite_backup.py')


load_modular_part(__file__, 'db_persist_parts/part_009__normalized_repo.py')


load_modular_part(__file__, 'db_persist_parts/part_010_github_enabled.py')


load_modular_part(__file__, 'db_persist_parts/part_011__github_request.py')


load_modular_part(__file__, 'db_persist_parts/part_012__github_repo_check.py')


load_modular_part(__file__, 'db_persist_parts/part_013__github_get_sha.py')


load_modular_part(__file__, 'db_persist_parts/part_014__sqlite_snapshot_to_temp.py')


load_modular_part(__file__, 'db_persist_parts/part_015_github_upload_db.py')


load_modular_part(__file__, 'db_persist_parts/part_016_github_remote_user_count.py')


load_modular_part(__file__, 'db_persist_parts/part_017_github_download_db.py')


# آخرین وضعیت ریستور (برای پیام ادمین)
_LAST_RESTORE_STATUS: dict[str, str | bool | int] = {
    "ok": False,
    "msg": "",
    "local_users": 0,
    "remote_users": -1,
}


load_modular_part(__file__, 'db_persist_parts/part_018_get_last_restore_status.py')


load_modular_part(__file__, 'db_persist_parts/part_019_auto_restore_if_empty.py')


load_modular_part(__file__, 'db_persist_parts/part_020_auto_backup.py')


load_modular_part(__file__, 'db_persist_parts/part_021_send_db_to_admins_sync.py')


load_modular_part(__file__, 'db_persist_parts/part_022_shutdown_backup.py')


load_modular_part(__file__, 'db_persist_parts/part_023_send_db_to_admins.py')


load_modular_part(__file__, 'db_persist_parts/part_024_restore_db_from_file.py')


load_modular_part(__file__, 'db_persist_parts/part_025_notify_admins_if_empty.py')
