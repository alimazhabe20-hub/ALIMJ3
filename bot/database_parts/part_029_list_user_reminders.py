# Auto-split part 29: list_user_reminders
def list_user_reminders(user_id, limit=20):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT id, text, remind_at, COALESCE(repeat_type,'once'), COALESCE(repeat_every,0), "
        "COALESCE(done,0), COALESCE(active,1) FROM reminders "
        "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    )
    rows = c.fetchall()
    conn.close()
    return rows
