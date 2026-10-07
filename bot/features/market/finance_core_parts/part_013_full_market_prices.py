# Auto-split part 13: full_market_prices
async def full_market_prices() -> str:
    """قیمت بازار بدون کریپتو — خروجی جدولی و بدون عدد حدسی."""
    from bot.utils.table_renderer import render_table

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

    rows = []
    for label, key in [
        ("💵 دلار", "dollar"), ("💶 یورو", "euro"), ("💷 پوند", "pound"),
        ("🇦🇪 درهم", "dirham"), ("🇹🇷 لیر", "lira"),
        ("🇨🇳 یوان", "yuan"), ("🇷🇺 روبل", "ruble"),
        ("🇦🇫 افغانی", "afghani"), ("🇮🇶 دینار عراق", "dinar_iq"),
        ("🥇 طلای ۱۸", "gold18"), ("🥈 نقره ۹۹۹", "silver"), ("🟠 مس", "copper"),
        ("🪙 سکه امامی", "coin_emami"), ("🪙 سکه بهار", "coin_bahar"),
        ("🪙 نیم‌سکه", "coin_half"), ("🪙 ربع‌سکه", "coin_quarter"),
    ]:
        v = data.get(key)
        rows.append((label, pn(f"{v / 10:,.0f}") + " تومان" if v is not None else "—"))

    return (
        render_table(("بازار", "قیمت"), rows, title="💰 قیمت بازار")
        + "\n\n💡 کریپتو: از «۲۰ ارز برتر» یا تبدیل / نمودار / تحلیل استفاده کنید."
    )
