# Auto-split part 10: get_top_crypto
async def get_top_crypto(limit: int = 20) -> str:
    key = f"top_crypto_{limit}"
    now = datetime.now().timestamp()
    if key in _cache and now - _cache_t.get(key, 0) < 90:
        return _cache[key]

    usd_task = asyncio.create_task(_get_usd_rial())
    coins = []
    retries = max(0, int(__import__('os').getenv("MARKET_HTTP_RETRIES", "0")))

    try:
        async with pooled_async_client() as client:
            pages = max(1, (min(limit, 300) + 249) // 250)
            for page in range(1, pages + 1):
                r = await request_with_retry("GET", 
                    "https://api.coingecko.com/api/v3/coins/markets", retries=retries,
                    params={
                        "vs_currency": "usd",
                        "order": "market_cap_desc",
                        "per_page": min(250, limit - len(coins)),
                        "page": page,
                        "sparkline": "false",
                        "price_change_percentage": "24h",
                    },
                )
                if r.status_code != 200:
                    break
                batch = safe_json(r) or []
                if not batch:
                    break
                for coin in batch:
                    coins.append({
                        "symbol": (coin.get("symbol") or "").upper(),
                        "price": coin.get("current_price") or 0,
                        "chg": coin.get("price_change_percentage_24h") or 0,
                    })
                if len(coins) >= limit:
                    break
    except Exception as e:
        logger.error(f"coingecko markets: {e}")

    try:
        usd_rial = await usd_task or 0
    except Exception:
        usd_rial = 0

    if not coins:
        coins = await _top_from_coinlore(limit)
    if not coins:
        coins = await _top_from_paprika(limit)

    if not coins:
        return "❌ لیست کریپتو موقتاً در دسترس نیست.\nکمی بعد دوباره امتحان کنید."

    lines = [f"💎 {limit} ارز برتر کریپتو", "(دلار + تومان)", ""]
    for i, coin in enumerate(coins[:limit], 1):
        sym = coin.get("symbol") or "?"
        price = float(coin.get("price") or 0)
        chg = float(coin.get("chg") or 0)
        emoji = "🟢" if chg >= 0 else "🔴"
        toman = price * (usd_rial / 10) if usd_rial else 0
        p_str = f"${price:,.2f}" if price >= 1 else f"${price:.6f}"
        chg_str = f"{chg:+.1f}%" if chg else ""
        line = f"{pn(i)}. {sym} {emoji} {chg_str}".strip()
        line += f"\n   {p_str}"
        if toman:
            line += f"  ≈  {pn(f'{toman:,.0f}')} تومان"
        lines.append(line)

    result = "\n".join(lines)
    _cache[key] = result
    _cache_t[key] = now
    return result
