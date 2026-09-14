# Auto-split part 61: get_economic_calendar_alert_users
def get_economic_calendar_alert_users():
    conn = get_db_connection()
    try:
        return conn.execute(
            "SELECT p.user_id, p.lead_minutes, p.timezone, p.currencies, p.impact "
            "FROM economic_calendar_preferences p JOIN users u ON u.user_id=p.user_id "
            "WHERE p.alerts=1 AND u.subscribed=1"
        ).fetchall()
    finally:
        conn.close()
