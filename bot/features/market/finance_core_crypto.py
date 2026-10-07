"""finance_core: crypto responsibilities."""
from .finance_core_common import *  # noqa: F401,F403
from . import finance_core_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


async def resolve_coin_id(symbol: str) -> Optional[str]:
    """پیدا کردن شناسه CoinGecko از نماد یا نام — پشتیبانی تقریباً همه ارزها"""
    symbol = (symbol or "").lower().strip().replace(" ", "").replace("‌", "")
    if not symbol:
        return None
    if symbol in SYMBOL_TO_ID:
        return SYMBOL_TO_ID[symbol]

    cache_key = f"resolve_{symbol}"
    now = datetime.now().timestamp()
    if cache_key in _cache and now - _cache_t.get(cache_key, 0) < 3600:
        return _cache[cache_key]

    try:
        async with pooled_async_client() as c:
            r = await request_with_retry("GET", "https://api.coingecko.com/api/v3/search", params={"query": symbol})
            if r.status_code == 200:
                coins = safe_json(r).get("coins") or []
                if coins:
                    for coin in coins:
                        if (coin.get("symbol") or "").lower() == symbol:
                            cid = coin.get("id")
                            _cache[cache_key] = cid
                            _cache_t[cache_key] = now
                            return cid
                    cid = coins[0].get("id")
                    _cache[cache_key] = cid
                    _cache_t[cache_key] = now
                    return cid
    except Exception as e:
        logger.warning(f"resolve_coin_id {symbol}: {e}")
    return None

async def _crypto_simple(ids: list[str]) -> dict[str, Any]:
    key = "cg_" + ",".join(sorted(ids))
    now = datetime.now().timestamp()
    if key in _cache and now - _cache_t.get(key, 0) < 60:
        return _cache[key]
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    try:
        async with pooled_async_client() as client:
            r = await request_with_retry("GET", 
                "https://api.coingecko.com/api/v3/simple/price", retries=0,
                params={
                    "ids": ",".join(ids),
                    "vs_currencies": "usd",
                    "include_24hr_change": "true",
                    "include_market_cap": "true",
                    "include_24hr_vol": "true",
                },
            )
            if r.status_code == 200:
                data = safe_json(r)
                _cache[key] = data
                _cache_t[key] = now
                return data
    except Exception as e:
        logger.error(f"coingecko simple: {e}")

    mapping = {
        "bitcoin": "btc-bitcoin", "ethereum": "eth-ethereum", "tether": "usdt-tether",
        "binancecoin": "bnb-binance-coin", "solana": "sol-solana", "ripple": "xrp-xrp",
        "the-open-network": "ton-toncoin", "dogecoin": "doge-dogecoin", "cardano": "ada-cardano",
        "tron": "trx-tron", "chainlink": "link-chainlink", "litecoin": "ltc-litecoin",
        "polkadot": "dot-polkadot", "avalanche-2": "avax-avalanche", "shiba-inu": "shib-shiba-inu",
    }
    out = {}
    try:
        async with pooled_async_client() as client:
            for cid in ids:
                pid = mapping.get(cid)
                if not pid:
                    continue
                r = await request_with_retry("GET", f"https://api.coinpaprika.com/v1/tickers/{pid}", retries=0)
                if r.status_code == 200:
                    price = safe_json(r).get("quotes", {}).get("USD", {}).get("price")
                    if price:
                        out[cid] = {"usd": float(price)}
        if out:
            _cache[key] = out
            _cache_t[key] = now
            return out
    except Exception as e:
        logger.error(f"paprika simple: {e}")
    return {}

async def _top_from_coinlore(limit: int = 20) -> list[dict[str, Any]]:
    try:
        async with pooled_async_client() as client:
            r = await request_with_retry("GET", f"https://api.coinlore.net/api/tickers/?start=0&limit={limit}", retries=0)
            if r.status_code != 200:
                return []
            data = (safe_json(r) or {}).get("data") or []
            out = []
            for row in data:
                out.append({
                    "symbol": (row.get("symbol") or "").upper(),
                    "price": float(row.get("price_usd") or 0),
                    "chg": float(row.get("percent_change_24h") or 0),
                })
            return out
    except Exception as e:
        logger.error(f"coinlore: {e}")
        return []

async def _top_from_paprika(limit: int = 20) -> list[dict[str, Any]]:
    try:
        async with pooled_async_client() as client:
            r = await request_with_retry("GET", "https://api.coinpaprika.com/v1/tickers", retries=0)
            if r.status_code != 200:
                return []
            data = safe_json(r) or []
            data = sorted(data, key=lambda x: x.get("rank") or 9999)[:limit]
            out = []
            for row in data:
                q = (row.get("quotes") or {}).get("USD") or {}
                out.append({
                    "symbol": (row.get("symbol") or "").upper(),
                    "price": float(q.get("price") or 0),
                    "chg": float(q.get("percent_change_24h") or 0),
                })
            return out
    except Exception as e:
        logger.error(f"paprika top: {e}")
        return []

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

async def convert_crypto(amount: float, symbol: str) -> str:
    """تبدیل هر ارز دیجیتال به دلار و تومان — پشتیبانی تقریباً همه کوین‌ها"""
    symbol = symbol.lower().strip().replace(" ", "").replace("‌", "")
    coin_id = await resolve_coin_id(symbol)
    if not coin_id:
        return (
            "❌ ارز پیدا نشد.\n\n"
            "مثال‌ها:\n"
            "• 1.5 btc\n"
            "• 20 ton\n"
            "• 100 pepe\n"
            "• 50 sol\n"
            "• 10 sui"
        )
    prices = await _crypto_simple([coin_id])
    info = prices.get(coin_id) or {}
    usd_price = info.get("usd")
    if not usd_price:
        return "❌ قیمت این ارز در دسترس نیست."
    total_usd = amount * usd_price
    usd_rial = await _get_usd_rial() or 0
    total_toman = total_usd * (usd_rial / 10) if usd_rial else 0
    chg = info.get("usd_24h_change")
    mcap = info.get("usd_market_cap")
    vol = info.get("usd_24h_vol")

    price_str = f"${usd_price:,.8f}" if usd_price < 1 else (f"${usd_price:,.4f}" if usd_price < 1000 else f"${usd_price:,.2f}")
    lines = [
        "🔄 مبدل ارز دیجیتال",
        "────────────────────",
        f"از: {pn(amount)} {symbol.upper()}",
        f"قیمت واحد: {price_str}",
    ]
    if chg is not None:
        emoji = "🟢" if chg >= 0 else "🔴"
        lines.append(f"تغییر ۲۴س: {emoji} {chg:+.2f}%")
    lines.append("────────────────────")
    lines.append(f"💵 دلار: ${total_usd:,.4f}")
    lines.append(f"🇮🇷 تومان: {pn(f'{total_toman:,.0f}')}")
    if usd_rial:
        lines.append(f"📊 نرخ دلار: {pn(f'{usd_rial/10:,.0f}')} تومان")
    if mcap:
        lines.append(f"🏛 مارکت‌کپ: ${mcap:,.0f}")
    if vol:
        lines.append(f"📈 حجم ۲۴س: ${vol:,.0f}")
    # معکوس تقریبی
    if amount and total_usd:
        lines.append("────────────────────")
        lines.append(f"🔁 ۱ دلار ≈ {pn(f'{1/usd_price:,.6f}')} {symbol.upper()}" if usd_price else "")
        if total_toman and amount:
            per_toman = amount / total_toman if total_toman else 0
            if per_toman:
                lines.append(f"🔁 ۱ میلیون تومان ≈ {pn(f'{per_toman * 1_000_000:,.6f}')} {symbol.upper()}")
    return "\n".join([x for x in lines if x])

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
