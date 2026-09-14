# Auto-split part 2: set_workspace
def set_workspace(user_id: int, name: str, data: str) -> None:
    _execute_write("INSERT INTO v71_workspaces(user_id,name,data) VALUES(?,?,?) ON CONFLICT(user_id,name) DO UPDATE SET data=excluded.data,updated_at=CURRENT_TIMESTAMP", (user_id, name[:100], data[:30000]))
