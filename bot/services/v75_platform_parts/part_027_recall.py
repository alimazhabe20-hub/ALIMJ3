from typing import Any

# Auto-split part 27: recall
def recall(user_id:int, category:str|None=None, limit:int=20) -> list[dict[str,Any]]:
    conn=_db();
    if category:
        rows=conn.execute("SELECT category,key,value,confidence,source,updated_at FROM v75_memory WHERE user_id=? AND category=? ORDER BY updated_at DESC LIMIT ?",(user_id,category,min(MAX_MEMORY_ITEMS,limit))).fetchall()
    else:
        rows=conn.execute("SELECT category,key,value,confidence,source,updated_at FROM v75_memory WHERE user_id=? ORDER BY updated_at DESC LIMIT ?",(user_id,min(MAX_MEMORY_ITEMS,limit))).fetchall()
    conn.close(); return [dict(r) for r in rows]
