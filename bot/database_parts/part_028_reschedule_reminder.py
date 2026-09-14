# Auto-split part 28: reschedule_reminder
def reschedule_reminder(rid, next_at):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE reminders SET remind_at = ?, done = 0, active = 1 WHERE id = ?",
        (next_at, rid),
    )
    conn.commit()
    conn.close()
