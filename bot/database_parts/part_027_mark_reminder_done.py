# Auto-split part 27: mark_reminder_done
def mark_reminder_done(rid):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE reminders SET done = 1, active = 0 WHERE id = ?", (rid,))
    conn.commit()
    conn.close()
