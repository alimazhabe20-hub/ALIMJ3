"""Public database API compatibility facade.

Low-level connection, transaction and backup primitives are isolated in
``database_core.py``; feature repositories remain available from this module.
"""
from bot.utils.modular_loader import load_modular_part
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

load_modular_part(__file__, 'database_parts/part_001_init_db.py')



load_modular_part(__file__, 'database_parts/part_002_get_schema_status.py')


load_modular_part(__file__, 'database_parts/part_003_get_user.py')

load_modular_part(__file__, 'database_parts/part_004_save_user.py')

load_modular_part(__file__, 'database_parts/part_005_update_user_field.py')

load_modular_part(__file__, 'database_parts/part_006_get_all_users.py')

load_modular_part(__file__, 'database_parts/part_007_get_active_users_today.py')

load_modular_part(__file__, 'database_parts/part_008_update_stats.py')

load_modular_part(__file__, 'database_parts/part_009_get_user_city.py')

load_modular_part(__file__, 'database_parts/part_010_get_user_country.py')

load_modular_part(__file__, 'database_parts/part_011_get_user_language.py')


# ── تنظیمات اذان ──
# ستون‌ها: notification_enabled, notify_fajr, notify_dhuhr, notify_asr, notify_maghrib, notify_isha

AZAN_FIELDS = {
    "fajr": ("notify_fajr", "اذان صبح"),
    "dhuhr": ("notify_dhuhr", "اذان ظهر"),
    "asr": ("notify_asr", "اذان عصر"),
    "maghrib": ("notify_maghrib", "اذان مغرب"),
    "isha": ("notify_isha", "اذان عشاء"),
}


load_modular_part(__file__, 'database_parts/part_012_get_azan_settings.py')


load_modular_part(__file__, 'database_parts/part_013_set_azan_master.py')


load_modular_part(__file__, 'database_parts/part_014_toggle_azan_prayer.py')


load_modular_part(__file__, 'database_parts/part_015_get_users_for_azan.py')

load_modular_part(__file__, 'database_parts/part_016_get_last_main_msg_id.py')

load_modular_part(__file__, 'database_parts/part_017_set_last_main_msg_id.py')


# ── یادداشت و یادآوری و آمار شخصی ──

load_modular_part(__file__, 'database_parts/part_018_init_extra_tables.py')



load_modular_part(__file__, 'database_parts/part_019_get_sent_joke_hashes.py')


load_modular_part(__file__, 'database_parts/part_020_mark_joke_sent.py')


load_modular_part(__file__, 'database_parts/part_021_reset_sent_jokes.py')



load_modular_part(__file__, 'database_parts/part_022_add_note.py')


load_modular_part(__file__, 'database_parts/part_023_get_notes.py')


load_modular_part(__file__, 'database_parts/part_024_delete_note.py')


load_modular_part(__file__, 'database_parts/part_025_add_reminder.py')


load_modular_part(__file__, 'database_parts/part_026_get_pending_reminders.py')


load_modular_part(__file__, 'database_parts/part_027_mark_reminder_done.py')


load_modular_part(__file__, 'database_parts/part_028_reschedule_reminder.py')


load_modular_part(__file__, 'database_parts/part_029_list_user_reminders.py')


load_modular_part(__file__, 'database_parts/part_030_cancel_reminder.py')


# ── حافظه بلندمدت AI ────────────────────────────────────────────────────────

load_modular_part(__file__, 'database_parts/part_031_set_ai_memory.py')


load_modular_part(__file__, 'database_parts/part_032_get_ai_memory.py')


load_modular_part(__file__, 'database_parts/part_033_delete_ai_memory.py')


load_modular_part(__file__, 'database_parts/part_034_get_ai_history_summary.py')


load_modular_part(__file__, 'database_parts/part_035_set_ai_history_summary.py')


load_modular_part(__file__, 'database_parts/part_036_clear_ai_history_summary.py')


load_modular_part(__file__, 'database_parts/part_037_record_agent_outcome.py')


load_modular_part(__file__, 'database_parts/part_038_get_agent_tool_reliability.py')


load_modular_part(__file__, 'database_parts/part_039_get_agent_learning.py')

load_modular_part(__file__, 'database_parts/part_040_track_usage.py')


load_modular_part(__file__, 'database_parts/part_041_get_user_usage.py')


load_modular_part(__file__, 'database_parts/part_042_set_birth_date.py')


load_modular_part(__file__, 'database_parts/part_043_get_birth_date.py')


# ── Smart UX preferences ───────────────────────────────────────────────────

load_modular_part(__file__, 'database_parts/part_044_get_user_preferences.py')


load_modular_part(__file__, 'database_parts/part_045_set_user_preference.py')


load_modular_part(__file__, 'database_parts/part_046_clear_user_preferences.py')


load_modular_part(__file__, 'database_parts/part_047_get_top_user_features.py')


# ── Proactive automation preferences ───────────────────────────────────────

load_modular_part(__file__, 'database_parts/part_048_get_automation_preferences.py')


load_modular_part(__file__, 'database_parts/part_049_set_daily_digest.py')


load_modular_part(__file__, 'database_parts/part_050_get_users_for_daily_digest.py')


load_modular_part(__file__, 'database_parts/part_051_mark_daily_digest_sent.py')


load_modular_part(__file__, 'database_parts/part_052_get_upcoming_user_reminders.py')


# ── AI provider preference (per user) ──────────────────────────────────────

load_modular_part(__file__, 'database_parts/part_053_get_ai_preference.py')


load_modular_part(__file__, 'database_parts/part_054_set_ai_preference.py')


load_modular_part(__file__, 'database_parts/part_055_clear_ai_preference.py')


# ── تقویم اقتصادی ───────────────────────────────────────────────────────────

load_modular_part(__file__, 'database_parts/part_056_get_economic_calendar_preferences.py')


load_modular_part(__file__, 'database_parts/part_057_set_economic_calendar_preferences.py')


load_modular_part(__file__, 'database_parts/part_058_upsert_economic_calendar_events.py')


load_modular_part(__file__, 'database_parts/part_059_get_economic_calendar_event.py')


load_modular_part(__file__, 'database_parts/part_060_get_economic_calendar_events.py')


load_modular_part(__file__, 'database_parts/part_061_get_economic_calendar_alert_users.py')


load_modular_part(__file__, 'database_parts/part_062_economic_calendar_alert_was_sent.py')


load_modular_part(__file__, 'database_parts/part_063_mark_economic_calendar_alert_sent.py')
