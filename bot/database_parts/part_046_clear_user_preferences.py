# Auto-split part 46: clear_user_preferences
def clear_user_preferences(user_id):
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM user_preferences WHERE user_id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()
