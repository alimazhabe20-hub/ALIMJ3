# Auto-split part 33: delete_ai_memory
def delete_ai_memory(user_id, key=None):
    conn = get_db_connection()
    c = conn.cursor()
    if key:
        c.execute("DELETE FROM ai_memory WHERE user_id = ? AND key = ?", (user_id, key))
    else:
        c.execute("DELETE FROM ai_memory WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
