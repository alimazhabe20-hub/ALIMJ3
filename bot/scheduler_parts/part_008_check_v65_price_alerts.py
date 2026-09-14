# Auto-split part 8: check_v65_price_alerts
async def check_v65_price_alerts(context):
    """Check persisted crypto price alerts without exposing internal errors."""
    try:
        from bot.services.v61_v65_platform import check_price_alerts
        from bot.features.market.finance_core import resolve_coin_id, _crypto_simple
        async def fetch(symbol):
            cid = await resolve_coin_id(symbol)
            if not cid: raise ValueError("unknown symbol")
            data = await _crypto_simple([cid])
            row = data.get(cid) or {}
            return float(row["usd"])
        hits = await check_price_alerts(fetch)
        from bot.services.v71_platform import notification_claim
        for uid, aid, symbol, target, value in hits:
            try:
                dedupe=f"price:{aid}:{value:.8g}"
                if not notification_claim(uid, "price_alert", f"{symbol}:{value}", dedupe, ttl_seconds=300):
                    continue
                await context.bot.send_message(chat_id=uid, text=f"🔔 هشدار قیمت\n\n{symbol}: ${value:,.6g}\nهدف: {target:,.6g}")
            except Exception as exc:
                logger.debug("price alert delivery failed: %s", exc)
    except Exception as exc:
        logger.debug("v65 price alerts failed: %s", exc)
