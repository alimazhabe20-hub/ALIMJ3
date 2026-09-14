# Auto-split part 36: clear_ai_history_summary
def clear_ai_history_summary(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("DELETE FROM ai_history_summary WHERE user_id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()
