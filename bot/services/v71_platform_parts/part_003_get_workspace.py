# Auto-split part 3: get_workspace
def get_workspace(user_id: int, name: str) -> str | None:
    conn=get_db_connection(); r=conn.execute("SELECT data FROM v71_workspaces WHERE user_id=? AND name=?",(user_id,name[:100])).fetchone(); conn.close(); return r[0] if r else None
