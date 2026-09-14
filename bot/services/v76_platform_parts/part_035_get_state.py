from typing import Any

# Auto-split part 35: get_state
def get_state(user_id:int)->dict[str,Any]:
    c=_db();r=c.execute("SELECT goal,context_json,pending,updated_at FROM v76_state WHERE user_id=?",(user_id,)).fetchone();c.close()
    if not r:return {}
    try:ctx=json.loads(r[1] or "{}")
    except Exception:ctx={}
    return {"goal":r[0],"context":ctx,"pending":bool(r[2]),"updated_at":r[3]}
