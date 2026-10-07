from typing import Any

# Auto-split part 25: evaluate_alert
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
