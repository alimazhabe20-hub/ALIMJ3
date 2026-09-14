# Auto-split part 5: list_branches
def list_branches(user_id: int) -> list[str]:
    conn=get_db_connection(); rows=conn.execute("SELECT name FROM v71_branches WHERE user_id=? ORDER BY updated_at DESC",(user_id,)).fetchall(); conn.close(); return [r[0] for r in rows]
