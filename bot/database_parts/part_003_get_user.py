from typing import Any

# Auto-split part 3: get_user
def get_user(user_id: int) -> tuple[Any, ...] | None:
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result
