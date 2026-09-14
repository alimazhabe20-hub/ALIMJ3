# Auto-split part 30: cancel_reminder
def cancel_reminder(user_id, rid):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE reminders SET done = 1, active = 0 WHERE id = ? AND user_id = ?",
        (rid, user_id),
    )
    conn.commit()
    n = c.rowcount
    conn.close()
    return n > 0
