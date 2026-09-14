# Auto-split part 63: mark_economic_calendar_alert_sent
def mark_economic_calendar_alert_sent(user_id, event_id):
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO economic_calendar_sent(user_id,event_id,sent_at) VALUES(?,?,datetime('now'))",
            (user_id, event_id),
        )
        conn.commit()
    finally:
        conn.close()
