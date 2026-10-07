"""v77_platform: alerts responsibilities."""
from .v77_platform_common import *  # noqa: F401,F403
from . import v77_platform_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def evaluate_alert(kind: str, config: dict[str,Any], context: dict[str,Any]) -> bool:
    try:
        if kind=="price":
            v=float(context["price"]);t=float(config["target"]);return v>=t if config.get("direction","above")=="above" else v<=t
        if kind=="change":
            v=float(context["change_pct"]);t=abs(float(config["threshold"]));return v>=t if config.get("direction","above")=="above" else v<=-t
        if kind=="news":return float(context.get("impact",0))>=float(config.get("min_impact",.7))
        if kind=="calendar":return abs(float(context.get("surprise",0)))>=float(config.get("min_surprise",.5))
        if kind=="combo":return all(bool(context.get(k)) for k in config.get("all",[])[:20])
    except (TypeError,ValueError,KeyError):return False
    return False

def create_alert(user_id: int, kind: str, config: dict[str,Any]) -> str:
    aid=uuid.uuid4().hex;c=_db();c.execute("INSERT INTO v77_alerts(id,user_id,kind,config_json,enabled) VALUES(?,?,?,?,1)",(aid,int(user_id),str(kind)[:50],json.dumps(config,ensure_ascii=False)[:8000]));c.commit();c.close();return aid

def list_alerts(user_id: int, limit: int=50) -> list[dict[str,Any]]:
    c=_db();rows=c.execute("SELECT id,kind,config_json,enabled,created_at FROM v77_alerts WHERE user_id=? ORDER BY created_at DESC LIMIT ?",(int(user_id),max(1,min(100,int(limit))))).fetchall();c.close();out=[]
    for r in rows:
        try:cfg=json.loads(r[2] or "{}")
        except Exception:cfg={}
        out.append({"id":r[0],"kind":r[1],"config":cfg,"enabled":bool(r[3]),"created_at":r[4]})
    return out

def rate_limit(key: str, limit: int=30, window: float=60) -> bool:
    now=time.monotonic(); q=_RATE[str(key)]
    while q and now-q[0]>window:q.popleft()
    if len(q)>=max(1,int(limit)):return False
    q.append(now);return True

def circuit_state(name: str) -> dict[str,Any]:
    p=_CIRCUITS.setdefault(str(name),{"failures":0,"opened_until":0.0})
    return {"open":time.monotonic()<p["opened_until"],"failures":p["failures"],"retry_at":p["opened_until"]}

def record_failure(name: str, threshold: int=5, cooldown: float=60) -> None:
    n=str(name);now=time.monotonic();q=_FAILURES[n];q.append(now);p=_CIRCUITS.setdefault(n,{"failures":0,"opened_until":0.0});p["failures"]=len(q)
    if len(q)>=threshold:p["opened_until"]=now+max(1,float(cooldown))

def record_success(name: str) -> None:
    n=str(name);_FAILURES[n].clear();p=_CIRCUITS.setdefault(n,{"failures":0,"opened_until":0.0});p.update(failures=0,opened_until=0.0)
