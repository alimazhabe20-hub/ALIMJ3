# Auto-split part 26: get_pending_reminders
def get_pending_reminders(before_time=None):
    conn = get_db_connection()
    c = conn.cursor()
    if before_time:
        c.execute(
            "SELECT id, user_id, text, remind_at, COALESCE(repeat_type,'once'), "
            "COALESCE(repeat_every,0), COALESCE(active,1) "
            "FROM reminders WHERE done = 0 AND COALESCE(active,1) = 1 AND remind_at <= ?",
            (before_time,),
        )
    else:
        c.execute(
            "SELECT id, user_id, text, remind_at, COALESCE(repeat_type,'once'), "
            "COALESCE(repeat_every,0), COALESCE(active,1) "
            "FROM reminders WHERE done = 0 AND COALESCE(active,1) = 1"
        )
    rows = c.fetchall()
    conn.close()
    return rows
