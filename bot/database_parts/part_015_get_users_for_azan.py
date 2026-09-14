# Auto-split part 15: get_users_for_azan
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
