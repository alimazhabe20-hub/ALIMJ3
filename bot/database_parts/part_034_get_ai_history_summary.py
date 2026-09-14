# Auto-split part 34: get_ai_history_summary
def get_ai_history_summary(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT summary FROM ai_history_summary WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        return row[0] if row and row[0] else ""
    except Exception:
        return ""
    finally:
        conn.close()
