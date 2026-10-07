"""v75_platform: memory responsibilities."""
from .v75_platform_common import *  # noqa: F401,F403
from . import v75_platform_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def remember(user_id:int, category:str, key:str, value:str, confidence:float=1.0, source:str="user") -> None:
    conn=_db(); conn.execute("INSERT INTO v75_memory(id,user_id,category,key,value,confidence,source) VALUES(?,?,?,?,?,?,?) ON CONFLICT(user_id,category,key) DO UPDATE SET value=excluded.value,confidence=excluded.confidence,source=excluded.source,updated_at=CURRENT_TIMESTAMP",(uuid.uuid4().hex,user_id,category,key,redact(value,2000),max(0,min(1,float(confidence))),source)); conn.commit(); conn.close()

def recall(user_id:int, category:str|None=None, limit:int=20) -> list[dict[str,Any]]:
    conn=_db();
    if category:
        rows=conn.execute("SELECT category,key,value,confidence,source,updated_at FROM v75_memory WHERE user_id=? AND category=? ORDER BY updated_at DESC LIMIT ?",(user_id,category,min(MAX_MEMORY_ITEMS,limit))).fetchall()
    else:
        rows=conn.execute("SELECT category,key,value,confidence,source,updated_at FROM v75_memory WHERE user_id=? ORDER BY updated_at DESC LIMIT ?",(user_id,min(MAX_MEMORY_ITEMS,limit))).fetchall()
    conn.close(); return [dict(r) for r in rows]

def create_workspace(user_id:int,name:str) -> str:
    wid=uuid.uuid4().hex; conn=_db(); conn.execute("INSERT INTO v75_workspaces(id,user_id,name) VALUES(?,?,?)",(wid,user_id,redact(name,100))); conn.commit(); conn.close(); return wid
