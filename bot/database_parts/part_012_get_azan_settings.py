# Auto-split part 12: get_azan_settings
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
