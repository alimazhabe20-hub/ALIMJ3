from typing import Any

# Auto-split part 6: get_all_users
def get_all_users() -> list[tuple[Any, ...]]:
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT user_id, first_name, city, language FROM users WHERE subscribed = 1")
    result = c.fetchall()
    conn.close()
    return result
