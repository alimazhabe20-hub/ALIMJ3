from typing import Any

# Auto-split part 31: recall
def recall(user_id:int,category:str|None=None,limit:int=20)->list[dict[str,Any]]:
    c=_db(); q="SELECT category,key,value,confidence,source,updated_at FROM v76_memory WHERE user_id=?"; a=[user_id]
    if category:q+=" AND category=?";a.append(category)
    q+=" ORDER BY updated_at DESC LIMIT ?";a.append(max(1,min(100,int(limit)))); rows=c.execute(q,a).fetchall();c.close();return [dict(x) for x in rows]
