from typing import Any

# Auto-split part 41: list_alerts
def list_alerts(user_id: int, limit: int=50) -> list[dict[str,Any]]:
    c=_db();rows=c.execute("SELECT id,kind,config_json,enabled,created_at FROM v77_alerts WHERE user_id=? ORDER BY created_at DESC LIMIT ?",(int(user_id),max(1,min(100,int(limit))))).fetchall();c.close();out=[]
    for r in rows:
        try:cfg=json.loads(r[2] or "{}")
        except Exception:cfg={}
        out.append({"id":r[0],"kind":r[1],"config":cfg,"enabled":bool(r[3]),"created_at":r[4]})
    return out
