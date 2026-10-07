# Auto-split part 13: full_market_prices
async def full_market_prices() -> str:
    """قیمت بازار بدون کریپتو — یک درخواست JSON (سریع)"""
    bulk = await _fetch_tgju_bulk()
    data = {}
    for key, slug in TGJU_SLUGS.items():
        item = bulk.get(slug)
        if isinstance(item, dict):
            data[key] = _parse_price(item.get("p"))
        else:
            data[key] = _parse_price(item)
        if key == "silver" and data[key] is None:
            alt = bulk.get("silver")
            if isinstance(alt, dict):
                p = _parse_price(alt.get("p"))
                if p and p > 1000:
                    data[key] = p

    lines = ["💰 **قیمت بازار** (بدون کریپتو)\n"]

    def fmt(label: str, key: str, unit: str = "ریال") -> str:
        v = data.get(key)
        if v is None:
            return f"{label}: —"
        toman = v / 10
        return f"{label}: {pn(f'{v:,}')} {unit}  ({pn(f'{toman:,.0f}')} تومان)"

    lines.append("—— ارز ——")
    for label, key in [
        ("💵 دلار", "dollar"), ("💶 یورو", "euro"), ("💷 پوند", "pound"),
        ("🇦🇪 درهم", "dirham"), ("🇹🇷 لیر", "lira"),
        ("🇨🇳 یوان", "yuan"), ("🇷🇺 روبل", "ruble"),
        ("🇦🇫 افغانی", "afghani"), ("🇮🇶 دینار عراق", "dinar_iq"),
    ]:
        lines.append(fmt(label, key))

    lines.append("\n—— فلزات و سکه ——")
    for label, key in [
        ("🥇 طلای ۱۸", "gold18"), ("🥈 نقره ۹۹۹", "silver"), ("🟠 مس", "copper"),
        ("🪙 سکه امامی", "coin_emami"), ("🪙 سکه بهار", "coin_bahar"),
        ("🪙 نیم‌سکه", "coin_half"), ("🪙 ربع‌سکه", "coin_quarter"),
    ]:
        lines.append(fmt(label, key))

    lines.append("\n💡 کریپتو: از دکمه «۲۰ ارز برتر» یا تبدیل / نمودار / تحلیل استفاده کنید.")
    return "\n".join(lines)
