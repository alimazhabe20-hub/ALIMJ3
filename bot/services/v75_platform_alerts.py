"""v75_platform: alerts responsibilities."""
from .v75_platform_common import *  # noqa: F401,F403
from . import v75_platform_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def create_alert(user_id:int, kind:str, config:dict[str,Any]) -> str:
    conn=_db(); count=conn.execute("SELECT COUNT(*) FROM v75_alerts WHERE user_id=?",(user_id,)).fetchone()[0]
    if count>=MAX_ALERTS_PER_USER: conn.close(); raise ValueError("alert_limit")
    aid=uuid.uuid4().hex; conn.execute("INSERT INTO v75_alerts(id,user_id,kind,config_json) VALUES(?,?,?,?)",(aid,user_id,kind,json.dumps(config,ensure_ascii=False))); conn.commit(); conn.close(); return aid

def evaluate_alert(alert:dict[str,Any], context:dict[str,Any]) -> bool:
    if not alert.get("enabled",True): return False
    cfg=alert.get("config",{})
    kind=alert.get("kind","")
    if kind=="price":
        value=float(context.get("price",0)); target=float(cfg.get("target",0)); direction=cfg.get("direction","above")
        return value>=target if direction=="above" else value<=target
    if kind=="news": return float(context.get("impact",0))>=float(cfg.get("min_impact",.7))
    if kind=="calendar": return float(context.get("surprise",0))>=float(cfg.get("min_surprise",.5))
    if kind=="combo": return all(bool(context.get(k)) for k in cfg.get("all",[]))
    return False
