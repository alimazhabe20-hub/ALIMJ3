# Auto-split part 53: get_ai_preference
def get_ai_preference(user_id):
    """Returns (provider, model) or None. model='*' means all models of provider."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute(
            "SELECT provider, model FROM ai_preferences WHERE user_id = ?",
            (user_id,),
        )
        row = c.fetchone()
        if row:
            return (row[0], row[1] or "*")
        return None
    except Exception:
        return None
    finally:
        conn.close()
