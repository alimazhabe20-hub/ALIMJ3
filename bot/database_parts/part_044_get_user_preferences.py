# Auto-split part 44: get_user_preferences
def get_user_preferences(user_id):
    """Return lightweight UX preferences without exposing raw conversation data."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute(
            "SELECT response_style, currency FROM user_preferences WHERE user_id = ?",
            (user_id,),
        )
        row = c.fetchone()
        if not row:
            return {"response_style": "balanced", "currency": "USD"}
        return {"response_style": row[0] or "balanced", "currency": row[1] or "USD"}
    finally:
        conn.close()
