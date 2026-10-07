# Auto-split part 4: save_branch
def save_branch(user_id: int, name: str, context: str) -> None:
    _execute_write("INSERT INTO v71_branches(user_id,name,context) VALUES(?,?,?) ON CONFLICT(user_id,name) DO UPDATE SET context=excluded.context,updated_at=CURRENT_TIMESTAMP",(user_id,name[:100],context[:30000]))
