# Auto-split part 52: get_upcoming_user_reminders
def get_upcoming_user_reminders(user_id, now_iso, limit=5):
    conn = get_db_connection()
    try:
        return conn.execute(
            "SELECT text, remind_at, COALESCE(repeat_type,'once') FROM reminders "
            "WHERE user_id = ? AND done = 0 AND COALESCE(active,1) = 1 AND remind_at >= ? "
            "ORDER BY remind_at ASC LIMIT ?",
            (user_id, now_iso, max(1, int(limit))),
        ).fetchall()
    finally:
        conn.close()
