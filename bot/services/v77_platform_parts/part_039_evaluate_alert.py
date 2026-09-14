from typing import Any

# Auto-split part 39: evaluate_alert
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
