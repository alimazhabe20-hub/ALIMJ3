# Auto-split part 55: clear_ai_preference
def clear_ai_preference(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("DELETE FROM ai_preferences WHERE user_id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()
