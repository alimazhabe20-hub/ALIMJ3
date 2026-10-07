from typing import Any

# Auto-split part 22: market_summary
def market_summary(data: dict[str, Any]) -> str:
    lines = [f"📊 {str(data.get('symbol') or '').upper()}"]
    if data.get("price_usd") is not None: lines.append(f"💵 ${float(data['price_usd']):,.8g}")
    lines.append(f"🧭 Bias: {data.get('bias','mixed')} | Risk: {data.get('risk','high')}")
    for tf, ta in (data.get("timeframes") or {}).items():
        if "error" in ta: lines.append(f"• {tf}: unavailable"); continue
        lines.append(f"• {tf}: {ta.get('trend','neutral')} | RSI={ta.get('rsi') if ta.get('rsi') is not None else '-'} | ADX={ta.get('adx') if ta.get('adx') is not None else '-'}")
    lines.append("⚠️ تحلیل آموزشی است و تضمین سود نیست.")
    return "\n".join(lines)
