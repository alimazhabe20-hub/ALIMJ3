# Auto-split part 62: economic_calendar_alert_was_sent
def economic_calendar_alert_was_sent(user_id, event_id):
    conn = get_db_connection()
    try:
        return conn.execute(
            "SELECT 1 FROM economic_calendar_sent WHERE user_id=? AND event_id=?",
            (user_id, event_id),
        ).fetchone() is not None
    finally:
        conn.close()
