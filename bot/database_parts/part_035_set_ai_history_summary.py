# Auto-split part 35: set_ai_history_summary
def set_ai_history_summary(user_id, summary):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO ai_history_summary (user_id, summary, updated_at) VALUES (?, ?, datetime('now')) "
        "ON CONFLICT(user_id) DO UPDATE SET summary = excluded.summary, updated_at = datetime('now')",
        (user_id, (summary or "")[:4000]),
    )
    conn.commit()
    conn.close()
