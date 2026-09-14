from typing import Any

# Auto-split part 34: update_state
def update_state(user_id:int,goal:str,context:dict[str,Any]|None=None,pending:bool=False)->None:
    c=_db();c.execute("INSERT INTO v76_state(user_id,goal,context_json,pending,updated_at) VALUES(?,?,?,?,CURRENT_TIMESTAMP) ON CONFLICT(user_id) DO UPDATE SET goal=excluded.goal,context_json=excluded.context_json,pending=excluded.pending,updated_at=CURRENT_TIMESTAMP",(user_id,redact(goal,1000),json.dumps(context or {},ensure_ascii=False)[:10000],int(pending)));c.commit();c.close()
