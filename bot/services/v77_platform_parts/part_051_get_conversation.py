from typing import Any
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from bot.services.v77_platform import MAX_STATE_TURNS

# Auto-split part 51: get_conversation
def get_conversation(user_id: int, limit: int=MAX_STATE_TURNS) -> list[dict[str,Any]]:
    c=_db();rows=c.execute("SELECT role,content,metadata_json,created_at FROM v77_conversation WHERE user_id=? ORDER BY created_at DESC LIMIT ?",(int(user_id),max(1,min(MAX_STATE_TURNS,int(limit))))).fetchall();c.close();out=[]
    for r in reversed(rows):
        try:m=json.loads(r[2] or "{}")
        except Exception:m={}
        out.append({"role":r[0],"content":r[1],"metadata":m,"created_at":r[3]})
    return out
