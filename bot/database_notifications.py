"""database: notifications responsibilities."""
from .database_common import *  # noqa: F401,F403
from . import database_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def get_azan_settings(user_id):
    """
    برگرداندن تنظیمات اذان کاربر.
    خروجی: {
      enabled: bool,
      fajr, dhuhr, asr, maghrib, isha: bool
    }
    """
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute(
            """SELECT COALESCE(notification_enabled, 0),
                      COALESCE(notify_fajr, 0),
                      COALESCE(notify_dhuhr, 0),
                      COALESCE(notify_asr, 0),
                      COALESCE(notify_maghrib, 0),
                      COALESCE(notify_isha, 0)
               FROM users WHERE user_id = ?""",
            (user_id,),
        )
        row = c.fetchone()
    except Exception:
        row = None
    finally:
        conn.close()
    if not row:
        return {
            "enabled": False,
            "fajr": False, "dhuhr": False, "asr": False,
            "maghrib": False, "isha": False,
        }
    return {
        "enabled": bool(row[0]),
        "fajr": bool(row[1]),
        "dhuhr": bool(row[2]),
        "asr": bool(row[3]),
        "maghrib": bool(row[4]),
        "isha": bool(row[5]),
    }

def set_azan_master(user_id, enabled: bool):
    """روشن/خاموش کردن کل اعلان اذان"""
    update_user_field(user_id, "notification_enabled", 1 if enabled else 0)

def toggle_azan_prayer(user_id, prayer_key: str) -> bool:
    """
    روشن/خاموش کردن یک اذان خاص.
    prayer_key: fajr|dhuhr|asr|maghrib|isha
    برمی‌گرداند وضعیت جدید (True=روشن)
    """
    if prayer_key not in AZAN_FIELDS:
        return False
    field, _ = AZAN_FIELDS[prayer_key]
    settings = get_azan_settings(user_id)
    new_val = not settings.get(prayer_key, False)
    update_user_field(user_id, field, 1 if new_val else 0)
    return new_val

def get_users_for_azan():
    """
    کاربران فعال برای اعلان اذان.
    خروجی: لیست (user_id, city, enabled, fajr, dhuhr, asr, maghrib, isha)
    """
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute(
            """SELECT user_id, city,
                      COALESCE(notification_enabled, 0),
                      COALESCE(notify_fajr, 0),
                      COALESCE(notify_dhuhr, 0),
                      COALESCE(notify_asr, 0),
                      COALESCE(notify_maghrib, 0),
                      COALESCE(notify_isha, 0)
               FROM users
               WHERE subscribed = 1
                 AND COALESCE(notification_enabled, 0) = 1"""
        )
        rows = c.fetchall()
    except Exception as e:
        logger.error(f"get_users_for_azan: {e}")
        rows = []
    finally:
        conn.close()
    return rows
