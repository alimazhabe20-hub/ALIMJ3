# Auto-split part 31: set_ai_memory
def set_ai_memory(user_id, key, value):
    key = (key or "note").strip()[:80]
    value = (value or "").strip()[:1000]
    if not value:
        return
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO ai_memory (user_id, key, value, updated_at) VALUES (?, ?, ?, datetime('now')) "
        "ON CONFLICT(user_id, key) DO UPDATE SET value = excluded.value, updated_at = datetime('now')",
        (user_id, key, value),
    )
    conn.commit()
    conn.close()
