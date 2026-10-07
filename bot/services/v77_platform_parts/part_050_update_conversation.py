from typing import Any

# Auto-split part 50: update_conversation
def update_conversation(user_id: int, role: str, content: str, metadata: dict[str,Any]|None=None) -> None:
    if role not in {"user","assistant","tool","system"}:role="user"
    c=_db();c.execute("INSERT INTO v77_conversation(id,user_id,role,content,metadata_json) VALUES(?,?,?,?,?)",(uuid.uuid4().hex,int(user_id),role,redact(content,10000),json.dumps(metadata or {},ensure_ascii=False)[:6000]));c.execute("DELETE FROM v77_conversation WHERE user_id=? AND id NOT IN (SELECT id FROM v77_conversation WHERE user_id=? ORDER BY created_at DESC LIMIT ?)",(int(user_id),int(user_id),MAX_STATE_TURNS));c.commit();c.close()
