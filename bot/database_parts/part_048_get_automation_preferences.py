# Auto-split part 48: get_automation_preferences
def get_automation_preferences(user_id):
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT daily_digest, last_digest_date FROM automation_preferences WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            return {"daily_digest": False, "last_digest_date": None}
        return {"daily_digest": bool(row[0]), "last_digest_date": row[1]}
    finally:
        conn.close()
