"""v75_platform: market responsibilities."""
from .v75_platform_common import *  # noqa: F401,F403
from . import v75_platform_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def market_intelligence_2(symbol: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    d = data or {}
    closes = [float(x) for x in d.get("closes", []) if isinstance(x,(int,float)) or str(x).replace('.','',1).isdigit()]
    if len(closes) >= 2:
        change = (closes[-1]-closes[0])/closes[0]*100 if closes[0] else 0
        trend = "bullish" if change > 1 else "bearish" if change < -1 else "neutral"
        volatility = sum(abs(closes[i]-closes[i-1])/closes[i-1] for i in range(1,len(closes)) if closes[i-1]) / max(1,len(closes)-1)*100
    else:
        change=0; trend="unknown"; volatility=0
    return {"symbol": symbol.upper(), "trend": trend, "change_pct": round(change,3), "volatility_pct": round(volatility,3),
            "confidence": round(min(0.95, 0.35 + min(len(closes), 100)/200),3),
            "scenarios": {"bullish": "continuation above resistance", "bearish": "break below support", "neutral": "range-bound"}}
