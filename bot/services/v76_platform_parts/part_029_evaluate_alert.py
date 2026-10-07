from typing import Any

# Auto-split part 29: evaluate_alert
def evaluate_alert(kind: str, config: dict[str,Any], context: dict[str,Any]) -> bool:
    if kind=="price":
        try: v=float(context["price"]); t=float(config["target"]); return v>=t if config.get("direction","above")=="above" else v<=t
        except Exception:return False
    if kind=="combo": return all(bool(context.get(k)) for k in config.get("all",[])[:20])
    if kind=="news": return float(context.get("impact",0))>=float(config.get("min_impact",.7))
    if kind=="calendar": return abs(float(context.get("surprise",0)))>=float(config.get("min_surprise",.5))
    return False
