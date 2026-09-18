# Auto-split part 66: delete_reminder
def delete_reminder(user_id, rid):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM reminders WHERE id=? AND user_id=?", (rid, user_id))
    conn.commit(); ok = c.rowcount > 0; conn.close(); return ok
