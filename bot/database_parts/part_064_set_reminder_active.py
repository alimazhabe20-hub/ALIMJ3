# Auto-split part 64: set_reminder_active
def set_reminder_active(user_id, rid, active):
    conn = get_db_connection()
    c = conn.cursor()
    if active:
        c.execute("UPDATE reminders SET active=1, done=0 WHERE id=? AND user_id=?", (rid, user_id))
    else:
        c.execute("UPDATE reminders SET active=0 WHERE id=? AND user_id=?", (rid, user_id))
    conn.commit()
    ok = c.rowcount > 0
    conn.close()
    return ok
