# Auto-split part 11: get_crypto_price
async def get_crypto_price(symbol: str = "btc") -> str:
    """قیمت لحظه‌ای یک رمزارز با دلار و تومان، با fallbackهای موجود."""
    symbol = (symbol or "btc").lower().strip().replace(" ", "").replace("‌", "")
    aliases = {
        "بیتکوین": "btc", "بیتکویین": "btc", "بیتكوين": "btc", "bitcoin": "btc",
        "اتریوم": "eth", "ethereum": "eth", "تتر": "usdt", "سولانا": "sol",
    }
    symbol = aliases.get(symbol, symbol)
    coin_id = await resolve_coin_id(symbol)
    if not coin_id:
        return f"❌ ارز «{symbol}» پیدا نشد."
    prices = await _crypto_simple([coin_id])
    info = prices.get(coin_id) or {}
    usd_price = info.get("usd")
    if usd_price is None:
        return f"❌ قیمت «{symbol.upper()}» موقتاً در دسترس نیست."
    usd_rial = await _get_usd_rial() or 0
    toman = float(usd_price) * (usd_rial / 10) if usd_rial else 0
    chg = info.get("usd_24h_change")
    price_str = f"${float(usd_price):,.8f}" if float(usd_price) < 1 else (f"${float(usd_price):,.4f}" if float(usd_price) < 1000 else f"${float(usd_price):,.2f}")
    lines = [f"💰 قیمت {symbol.upper()}", f"💵 دلار: {price_str}"]
    if toman:
        lines.append(f"🇮🇷 تومان: {pn(f'{toman:,.0f}')}")
    if chg is not None:
        lines.append(f"📊 تغییر ۲۴ساعت: {'🟢' if float(chg) >= 0 else '🔴'} {float(chg):+.2f}%")
    return "\n".join(lines)
