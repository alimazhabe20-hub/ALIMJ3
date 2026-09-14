# Auto-split part 54: set_ai_preference
def set_ai_preference(user_id, provider, model="*"):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO ai_preferences (user_id, provider, model, updated_at) "
            "VALUES (?, ?, ?, datetime('now')) "
            "ON CONFLICT(user_id) DO UPDATE SET "
            "provider = excluded.provider, model = excluded.model, "
            "updated_at = datetime('now')",
            (user_id, provider, model or "*"),
        )
        conn.commit()
    finally:
        conn.close()
