from bot.utils.modular_loader import load_modular_part
from datetime import time, datetime, timedelta
import pytz
from bot.logger import logger
from bot.database import (
    get_all_users,
    update_stats,
    get_users_for_azan,
    backup_db,
    get_pending_reminders,
    mark_reminder_done,
    reschedule_reminder,
    get_economic_calendar_alert_users, economic_calendar_alert_was_sent, mark_economic_calendar_alert_sent,
)
from bot.utils.helpers import build_message, get_refresh_button
from bot.config import config
from bot.api.prayer import get_prayer_times
from bot.db_persist import send_db_to_admins
import asyncio

PRAYER_FLAGS = {
    "اذان صبح": 3,
    "اذان ظهر": 4,
    "اذان عصر": 5,
    "اذان مغرب": 6,
    "اذان عشاء": 7,
}


load_modular_part(__file__, 'scheduler_parts/part_001_send_daily_messages.py')


load_modular_part(__file__, 'scheduler_parts/part_002_check_azan_notifications.py')


load_modular_part(__file__, 'scheduler_parts/part_003__next_occurrence.py')


load_modular_part(__file__, 'scheduler_parts/part_004_check_user_reminders.py')



load_modular_part(__file__, 'scheduler_parts/part_005_check_economic_calendar_alerts.py')

load_modular_part(__file__, 'scheduler_parts/part_006_periodic_backup.py')


load_modular_part(__file__, 'scheduler_parts/part_007_periodic_telegram_backup.py')



load_modular_part(__file__, 'scheduler_parts/part_008_check_v65_price_alerts.py')


load_modular_part(__file__, 'scheduler_parts/part_009_v70_due_jobs.py')


load_modular_part(__file__, 'scheduler_parts/part_010_v71_due_jobs.py')


load_modular_part(__file__, 'scheduler_parts/part_011_check_update_center.py')


load_modular_part(__file__, 'scheduler_parts/part_012_setup_scheduler.py')
