# Auto-split part 49: set_daily_digest
def set_daily_digest(user_id, enabled):
    enabled = 1 if enabled else 0
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO automation_preferences (user_id, daily_digest, updated_at) "
            "VALUES (?, ?, datetime('now')) "
            "ON CONFLICT(user_id) DO UPDATE SET daily_digest=excluded.daily_digest, updated_at=datetime('now')",
            (user_id, enabled),
        )
        conn.commit()
    finally:
        conn.close()
