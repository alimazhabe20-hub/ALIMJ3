# Auto-split part 42: set_birth_date
def set_birth_date(user_id, birth_date):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET birth_date = ? WHERE user_id = ?", (birth_date, user_id))
    conn.commit()
    conn.close()
