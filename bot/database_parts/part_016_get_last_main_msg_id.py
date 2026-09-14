# Auto-split part 16: get_last_main_msg_id
def get_last_main_msg_id(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT last_main_msg_id FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        return row[0] if row else None
    except Exception:
        return None
    finally:
        conn.close()
