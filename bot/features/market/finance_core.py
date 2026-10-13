"""Core market pricing, conversion and crypto-list operations extracted from finance.py.

This module is intentionally independent of the large finance facade. Public
legacy function names remain re-exported by ``finance.py`` for compatibility.
"""

# BEGIN MERGED LEGACY PART: finance_core_parts/part_001__get_usd_rial.py
# Auto-split part 1: _get_usd_rial
async def _get_usd_rial() -> int | None:
    return await _tgju_price("price_dollar_rl")

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: finance_core_parts/part_002_pn.py
from typing import Any

# Auto-split part 2: pn
def pn(n: Any) -> str:
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: finance_core_parts/part_003__parse_price.py
from typing import Any

# Auto-split part 3: _parse_price
def _parse_price(raw: Any) -> int | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return int(raw)
    text = str(raw).replace(",", "").replace("٬", "").replace(" ", "").strip()
    if not text:
        return None
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: finance_core_parts/part_004__fetch_tgju_bulk.py
from typing import Any

# Auto-split part 4: _fetch_tgju_bulk
async def _fetch_tgju_bulk() -> dict[str, Any]:
    now = datetime.now().timestamp()
    if _BULK_CACHE_KEY in _cache and now - _cache_t.get(_BULK_CACHE_KEY, 0) < _BULK_TTL:
        return _cache[_BULK_CACHE_KEY]

    current = {}
    async with pooled_async_client() as client:
        for url in _AJAX_URLS:
            try:
                r = await request_with_retry("GET", url, retries=0)
                if r.status_code == 200:
                    data = safe_json(r) or {}
                    current = data.get("current") or {}
                    if current:
                        break
            except (httpx.HTTPError, OSError, RuntimeError) as exc:
                logger.warning("tgju ajax %s: %s", url, exc)

    if current:
        _cache[_BULK_CACHE_KEY] = current
        _cache_t[_BULK_CACHE_KEY] = now
        return current
    # stale-while-error: market values are better than an avoidable outage.
    return _cache.get(_BULK_CACHE_KEY, {})

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: finance_core_parts/part_005__tgju_price.py
# Auto-split part 5: _tgju_price
async def _tgju_price(slug: str) -> int | None:
    key = f"tgju_{slug}"
    now = datetime.now().timestamp()
    if key in _cache and now - _cache_t.get(key, 0) < _BULK_TTL:
        return _cache[key]

    bulk = await _fetch_tgju_bulk()
    item = bulk.get(slug)
    if isinstance(item, dict):
        val = _parse_price(item.get("p"))
    else:
        val = _parse_price(item)

    if val is not None:
        _cache[key] = val
        _cache_t[key] = now
        return val

    try:
        url = f"https://www.tgju.org/profile/{slug}"
        async with pooled_async_client() as c:
            r = await request_with_retry("GET", url, retries=0)
            r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        tag = soup.find(attrs={"data-col": "info.last_trade.PDrCotVal"})
        if tag:
            val = _parse_price(tag.get_text(strip=True))
            if val:
                _cache[key] = val
                _cache_t[key] = now
                return val
    except Exception as e:
        logger.error(f"tgju fallback {slug}: {e}")
    return None

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: finance_core_parts/part_006_resolve_coin_id.py
from typing import Optional

# Auto-split part 6: resolve_coin_id
async def resolve_coin_id(symbol: str) -> Optional[str]:
    """شناسه CoinGecko از نماد/نام — تقریباً همه کوین‌ها + کش."""
    symbol = (symbol or "").lower().strip().replace(" ", "").replace("‌", "").replace("-", "")
    if not symbol:
        return None

    # نرمال‌سازی فارسی رایج
    fa_map = {
        "بیتکوین": "btc", "بیتکویین": "btc", "بیتكوين": "btc", "bitcoin": "btc",
        "اتریوم": "eth", "ethereum": "eth", "تتر": "usdt", "tether": "usdt",
        "تون": "ton", "toncoin": "ton", "سولانا": "sol", "solana": "sol",
        "کاردانو": "ada", "ریپل": "xrp", "دوج": "doge", "دوجکوین": "doge",
        "شیبا": "shib", "پپه": "pepe", "بیاننس": "bnb", "بایننس": "bnb",
    }
    symbol = fa_map.get(symbol, symbol)

    if symbol in SYMBOL_TO_ID:
        return SYMBOL_TO_ID[symbol]
    # گاهی کلید با خط تیره
    if symbol.replace("-", "") in {k.replace("-", ""): v for k, v in SYMBOL_TO_ID.items()}:
        for k, v in SYMBOL_TO_ID.items():
            if k.replace("-", "") == symbol.replace("-", ""):
                return v

    cache_key = f"resolve_{symbol}"
    now = datetime.now().timestamp()
    if cache_key in _cache and now - _cache_t.get(cache_key, 0) < 3600:
        return _cache[cache_key]

    # 1) CoinGecko search
    try:
        r = await request_with_retry(
            "GET", "https://api.coingecko.com/api/v3/search",
            params={"query": symbol}, retries=0,
        )
        if r is not None and getattr(r, "status_code", 0) == 200:
            coins = (safe_json(r) or {}).get("coins") or []
            if coins:
                # اولویت: نماد دقیق
                for coin in coins:
                    if (coin.get("symbol") or "").lower() == symbol:
                        cid = coin.get("id")
                        if cid:
                            _cache[cache_key] = cid
                            _cache_t[cache_key] = now
                            return cid
                # بعد: id دقیق
                for coin in coins:
                    if (coin.get("id") or "").lower() == symbol:
                        cid = coin.get("id")
                        if cid:
                            _cache[cache_key] = cid
                            _cache_t[cache_key] = now
                            return cid
                cid = coins[0].get("id")
                if cid:
                    _cache[cache_key] = cid
                    _cache_t[cache_key] = now
                    return cid
    except Exception as e:
        logger.warning(f"resolve_coin_id gecko {symbol}: {e}")

    # 2) CoinPaprika search
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            r = await client.get("https://api.coinpaprika.com/v1/search/", params={"q": symbol, "c": "currencies", "limit": 10})
            if r.status_code == 200:
                currencies = (r.json() or {}).get("currencies") or []
                for c in currencies:
                    if (c.get("symbol") or "").lower() == symbol:
                        # paprika id مثل btc-bitcoin — برای gecko نیاز به map نداریم
                        # ذخیره paprika id جدا در کش با پیشوند
                        pid = c.get("id")
                        if pid:
                            _cache[cache_key] = f"paprika:{pid}"
                            _cache_t[cache_key] = now
                            return f"paprika:{pid}"
                if currencies:
                    pid = currencies[0].get("id")
                    if pid:
                        _cache[cache_key] = f"paprika:{pid}"
                        _cache_t[cache_key] = now
                        return f"paprika:{pid}"
    except Exception as e:
        logger.debug(f"resolve paprika {symbol}: {e}")

    # 3) اگر نماد کوتاه است همان را به‌عنوان paprika نماد امتحان کن
    if 2 <= len(symbol) <= 10 and symbol.isascii():
        # بعداً در _crypto_simple با نماد مستقیم قیمت می‌گیریم
        _cache[cache_key] = f"symbol:{symbol.upper()}"
        _cache_t[cache_key] = now
        return f"symbol:{symbol.upper()}"

    return None


# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: finance_core_parts/part_007__crypto_simple.py
from typing import Any

# Auto-split part 7: _crypto_simple
async def _crypto_simple(ids: list[str]) -> dict[str, Any]:
    """قیمت برای هر کوین: Gecko / Paprika / Coinlore / CryptoCompare / نماد مستقیم."""
    ids = [str(i).strip() for i in (ids or []) if i]
    if not ids:
        return {}
    key = "cg_" + ",".join(sorted(ids))
    now = datetime.now().timestamp()
    if key in _cache and now - _cache_t.get(key, 0) < 45:
        return _cache[key]

    out: dict[str, Any] = {}
    gecko_ids = [i for i in ids if not i.startswith("paprika:") and not i.startswith("symbol:")]
    paprika_ids = {i: i.split(":", 1)[1] for i in ids if i.startswith("paprika:")}
    symbol_ids = {i: i.split(":", 1)[1] for i in ids if i.startswith("symbol:")}

    # --- CoinGecko batch ---
    if gecko_ids:
        try:
            r = await request_with_retry(
                "GET",
                "https://api.coingecko.com/api/v3/simple/price",
                retries=0,
                params={
                    "ids": ",".join(gecko_ids),
                    "vs_currencies": "usd",
                    "include_24hr_change": "true",
                    "include_market_cap": "true",
                    "include_24hr_vol": "true",
                },
            )
            if r is not None and getattr(r, "status_code", 0) == 200:
                data = safe_json(r) or {}
                if isinstance(data, dict):
                    for cid in gecko_ids:
                        info = data.get(cid)
                        if isinstance(info, dict) and info.get("usd") is not None:
                            out[cid] = info
        except Exception as e:
            logger.error(f"coingecko simple: {e}")

    # --- Paprika by known map + explicit paprika: ids ---
    paprika_map = {
        "bitcoin": "btc-bitcoin", "ethereum": "eth-ethereum", "tether": "usdt-tether",
        "binancecoin": "bnb-binance-coin", "solana": "sol-solana", "ripple": "xrp-xrp",
        "the-open-network": "ton-toncoin", "dogecoin": "doge-dogecoin", "cardano": "ada-cardano",
        "tron": "trx-tron", "chainlink": "link-chainlink", "litecoin": "ltc-litecoin",
        "polkadot": "dot-polkadot", "avalanche-2": "avax-avalanche", "shiba-inu": "shib-shiba-inu",
        "usd-coin": "usdc-usd-coin", "matic-network": "matic-polygon", "near": "near-near-protocol",
        "uniswap": "uni-uniswap", "cosmos": "atom-cosmos", "bitcoin-cash": "bch-bitcoin-cash",
        "pepe": "pepe-pepe", "sui": "sui-sui", "aptos": "apt-aptos", "arbitrum": "arb-arbitrum",
        "optimism": "op-optimism", "render-token": "rndr-render", "filecoin": "fil-filecoin",
        "stellar": "xlm-stellar", "hedera-hashgraph": "hbar-hedera-hashgraph",
        "internet-computer": "icp-internet-computer", "kaspa": "kas-kaspa",
    }

    async def _paprika_price(pid: str) -> dict | None:
        try:
            async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
                r = await client.get(f"https://api.coinpaprika.com/v1/tickers/{pid}")
                if r.status_code != 200:
                    return None
                q = (r.json() or {}).get("quotes", {}).get("USD") or {}
                price = q.get("price")
                if price is None:
                    return None
                return {
                    "usd": float(price),
                    "usd_24h_change": q.get("percent_change_24h"),
                    "usd_market_cap": q.get("market_cap"),
                    "usd_24h_vol": q.get("volume_24h"),
                }
        except Exception as e:
            logger.debug(f"paprika {pid}: {e}")
            return None

    for cid in list(gecko_ids):
        if cid in out:
            continue
        pid = paprika_map.get(cid)
        if not pid:
            continue
        info = await _paprika_price(pid)
        if info:
            out[cid] = info

    for full_id, pid in paprika_ids.items():
        if full_id in out:
            continue
        info = await _paprika_price(pid)
        if info:
            out[full_id] = info

    # --- Coinlore top list match for missing gecko ids ---
    missing_gecko = [c for c in gecko_ids if c not in out]
    if missing_gecko:
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                r = await client.get("https://api.coinlore.net/api/tickers/?start=0&limit=100")
                if r.status_code == 200:
                    data = r.json() or {}
                    rows = data.get("data") if isinstance(data, dict) else data
                    if isinstance(rows, list):
                        by_name = {}
                        by_sym = {}
                        for row in rows:
                            nameid = (row.get("nameid") or "").lower()
                            sym = (row.get("symbol") or "").lower()
                            if nameid:
                                by_name[nameid] = row
                            if sym:
                                by_sym[sym] = row
                        for cid in missing_gecko:
                            row = by_name.get(cid) or by_sym.get(cid.split("-")[0] if "-" in cid else cid)
                            # map common gecko id to lore nameid
                            lore_alias = {
                                "binancecoin": "binance-coin",
                                "matic-network": "polygon",
                                "avalanche-2": "avalanche",
                                "shiba-inu": "shiba-inu",
                                "the-open-network": "toncoin",
                            }.get(cid, cid)
                            row = row or by_name.get(lore_alias)
                            if not row:
                                continue
                            price = row.get("price_usd")
                            if price is None:
                                continue
                            out[cid] = {
                                "usd": float(price),
                                "usd_24h_change": float(row.get("percent_change_24h") or 0),
                                "usd_market_cap": float(row.get("market_cap_usd") or 0) or None,
                                "usd_24h_vol": float(row.get("volume24") or 0) or None,
                            }
        except Exception as e:
            logger.debug(f"coinlore batch: {e}")

    # --- CryptoCompare / symbol-based for symbol:XXX and remaining ---
    async def _cc_price(sym: str) -> float | None:
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                r = await client.get(
                    "https://min-api.cryptocompare.com/data/price",
                    params={"fsym": sym.upper(), "tsyms": "USD"},
                )
                if r.status_code == 200:
                    v = (r.json() or {}).get("USD")
                    return float(v) if v is not None else None
        except Exception as e:
            logger.debug(f"cc {sym}: {e}")
        return None

    async def _paprika_by_symbol(sym: str) -> dict | None:
        """جستجوی پاپریکا با نماد و گرفتن قیمت."""
        try:
            async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
                r = await client.get(
                    "https://api.coinpaprika.com/v1/search/",
                    params={"q": sym, "c": "currencies", "limit": 5},
                )
                if r.status_code != 200:
                    return None
                currencies = (r.json() or {}).get("currencies") or []
                pid = None
                for c in currencies:
                    if (c.get("symbol") or "").lower() == sym.lower():
                        pid = c.get("id")
                        break
                if not pid and currencies:
                    pid = currencies[0].get("id")
                if not pid:
                    return None
                return await _paprika_price(pid)
        except Exception as e:
            logger.debug(f"paprika symbol {sym}: {e}")
            return None

    id_to_sym = {
        "bitcoin": "BTC", "ethereum": "ETH", "tether": "USDT", "binancecoin": "BNB",
        "solana": "SOL", "ripple": "XRP", "dogecoin": "DOGE", "cardano": "ADA",
        "tron": "TRX", "litecoin": "LTC", "polkadot": "DOT", "chainlink": "LINK",
        "shiba-inu": "SHIB", "the-open-network": "TON", "avalanche-2": "AVAX",
        "usd-coin": "USDC", "matic-network": "MATIC", "near": "NEAR", "uniswap": "UNI",
        "cosmos": "ATOM", "bitcoin-cash": "BCH", "pepe": "PEPE", "sui": "SUI",
        "aptos": "APT", "arbitrum": "ARB", "optimism": "OP", "filecoin": "FIL",
        "stellar": "XLM", "render-token": "RENDER",
    }

    for cid in list(gecko_ids):
        if cid in out:
            continue
        sym = id_to_sym.get(cid) or (cid.upper() if len(cid) <= 6 and cid.isascii() else None)
        if not sym:
            # تلاش paprika با خود id به‌عنوان query
            info = await _paprika_by_symbol(cid)
            if info:
                out[cid] = info
            continue
        price = await _cc_price(sym)
        if price is not None:
            out[cid] = {"usd": price}
        else:
            info = await _paprika_by_symbol(sym)
            if info:
                out[cid] = info

    for full_id, sym in symbol_ids.items():
        if full_id in out:
            continue
        price = await _cc_price(sym)
        if price is not None:
            out[full_id] = {"usd": price}
            continue
        info = await _paprika_by_symbol(sym)
        if info:
            out[full_id] = info

    if out:
        _cache[key] = out
        _cache_t[key] = now
    return out


# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: finance_core_parts/part_008__top_from_coinlore.py
from typing import Any

# Auto-split part 8: _top_from_coinlore
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

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: finance_core_parts/part_009__top_from_paprika.py
from typing import Any

# Auto-split part 9: _top_from_paprika
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

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: finance_core_parts/part_010_get_top_crypto.py
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

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: finance_core_parts/part_011_get_crypto_price.py
# Auto-split part 11: get_crypto_price
async def get_crypto_price(symbol: str = "btc") -> str:
    """قیمت لحظه‌ای یک رمزارز با دلار و تومان، با fallbackهای موجود."""
    symbol = (symbol or "btc").lower().strip().replace(" ", "").replace("‌", "")
    aliases = {
        "بیتکوین": "btc", "بیتکویین": "btc", "بیتكوين": "btc", "bitcoin": "btc",
        "btc": "btc", "xbt": "btc",
        "اتریوم": "eth", "ethereum": "eth", "eth": "eth",
        "تتر": "usdt", "tether": "usdt", "usdt": "usdt",
        "سولانا": "sol", "solana": "sol", "sol": "sol",
        "تون": "ton", "toncoin": "ton", "ton": "ton",
    }
    symbol = aliases.get(symbol, symbol)
    if symbol in SYMBOL_TO_ID and symbol not in ("btc", "eth", "usdt", "sol", "ton"):
        # keep as-is; resolve_coin_id handles SYMBOL_TO_ID
        pass
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

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: finance_core_parts/part_012_convert_crypto.py
# Auto-split part 12: convert_crypto
async def convert_crypto(amount: float, symbol: str) -> str:
    """تبدیل هر ارز دیجیتال به دلار و تومان — پشتیبانی تقریباً همه کوین‌ها"""
    symbol = (symbol or "").lower().strip().replace(" ", "").replace("‌", "")
    # نرمال‌سازی نام فارسی → نماد
    _fa_sym = {
        "بیتکوین": "btc", "بیتکویین": "btc", "بیتكوين": "btc", "bitcoin": "btc",
        "اتریوم": "eth", "ethereum": "eth", "تتر": "usdt", "tether": "usdt",
        "تون": "ton", "toncoin": "ton", "سولانا": "sol", "solana": "sol",
        "کاردانو": "ada", "ریپل": "xrp", "دوج": "doge", "دوجکوین": "doge",
    }
    symbol = _fa_sym.get(symbol, symbol)
    if symbol in _FA_CURRENCY:
        symbol = _FA_CURRENCY.get(symbol, symbol)
    coin_id = await resolve_coin_id(symbol)
    if not coin_id:
        return (
            "❌ ارز پیدا نشد.\n\n"
            "تقریباً همه کوین‌های بازار پشتیبانی می‌شوند.\n"
            "مثال‌ها:\n"
            "• 1.5 btc یا ۲ بیتکوین\n"
            "• 20 ton\n"
            "• 100 pepe\n"
            "• 50 sol\n"
            "• 1000 not / dogs / jup / wif"
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

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: finance_core_parts/part_013_full_market_prices.py
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

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: finance_core_parts/part_014_rial_toman.py
# Auto-split part 14: rial_toman
def rial_toman(amount: float, to_toman: bool = True) -> str:
    if to_toman:
        return f"💵 {pn(f'{amount:,.0f}')} ریال = **{pn(f'{amount/10:,.0f}')} تومان**"
    return f"💵 {pn(f'{amount:,.0f}')} تومان = **{pn(f'{amount*10:,.0f}')} ریال**"

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: finance_core_parts/part_015_convert_currency.py
# Auto-split part 15: convert_currency
async def convert_currency(amount: float, from_cur: str, to_cur: str = "") -> str:
    """تبدیل ارز / کریپتو هوشمند — پشتیبانی گسترده + تبدیل دوطرفه"""
    from_cur = (from_cur or "").lower().strip().replace(" ", "").replace("‌", "")
    to_cur = (to_cur or "").lower().strip().replace(" ", "").replace("‌", "")

    from_cur = _FA_CURRENCY.get(from_cur, from_cur)
    to_cur = _FA_CURRENCY.get(to_cur, to_cur)

    # کریپتو → کریپتو یا کریپتو → فیات
    if from_cur in SYMBOL_TO_ID or re.match(r"^[a-zA-Z0-9]{2,15}$", from_cur):
        if to_cur and to_cur not in ("usd", "دلار", "toman", "تومان", "rial", "ریال", ""):
            id1 = await resolve_coin_id(from_cur)
            id2 = await resolve_coin_id(to_cur)
            if id1 and id2:
                prices = await _crypto_simple([id1, id2])
                p1 = prices.get(id1, {}).get("usd")
                p2 = prices.get(id2, {}).get("usd")
                if p1 and p2 and p2 > 0:
                    result = amount * p1 / p2
                    usd_rial = await _get_usd_rial() or 0
                    total_usd = amount * p1
                    total_toman = total_usd * (usd_rial / 10) if usd_rial else 0
                    return (
                        f"🔄 تبدیل کریپتو به کریپتو\n"
                        f"────────────────────\n"
                        f"{pn(amount)} {from_cur.upper()} = **{result:,.8f} {to_cur.upper()}**\n"
                        f"≈ ${total_usd:,.4f}\n"
                        + (f"≈ {pn(f'{total_toman:,.0f}')} تومان\n" if total_toman else "")
                        + f"────────────────────\n"
                        f"قیمت {from_cur.upper()}: ${p1:,.6f}\n"
                        f"قیمت {to_cur.upper()}: ${p2:,.6f}"
                    )
        return await convert_crypto(amount, from_cur)

    d = await _get_usd_rial()

    if from_cur in ("rial", "ریال", "irr") and to_cur in ("toman", "تومان", "tmn", ""):
        return rial_toman(amount, True)
    if from_cur in ("toman", "تومان", "tmn") and to_cur in ("rial", "ریال", "irr"):
        return rial_toman(amount, False)

    if d:
        if from_cur in ("usd",) and to_cur in ("rial", "toman", ""):
            rial = amount * d
            return (
                f"💵 تبدیل دلار\n"
                f"────────────────────\n"
                f"${amount:,.2f} = **{pn(f'{rial:,.0f}')} ریال**\n"
                f"≈ **{pn(f'{rial/10:,.0f}')} تومان**\n"
                f"نرخ: {pn(f'{d/10:,.0f}')} تومان"
            )
        if from_cur in ("toman",) and to_cur in ("usd", "دلار", ""):
            usd = amount * 10 / d
            return (
                f"🇮🇷 تبدیل تومان → دلار\n"
                f"────────────────────\n"
                f"{pn(f'{amount:,.0f}')} تومان = **${usd:,.4f}**\n"
                f"نرخ: {pn(f'{d/10:,.0f}')} تومان"
            )
        if from_cur in ("rial",) and to_cur in ("usd",):
            return f"{pn(f'{amount:,.0f}')} ریال = **${amount / d:,.4f}**"

    # هر نماد ناشناخته‌ای را به‌عنوان کریپتو امتحان کن (تقریباً همه کوین‌ها)
    _from_norm = (from_cur or "").lower().strip().replace(" ", "").replace("‌", "")
    _fiat = {"usd", "eur", "gbp", "toman", "rial", "irr", "aed", "try", "cny", "rub", "tmn"}
    if _from_norm and _from_norm not in _fiat:
        return await convert_crypto(amount, _from_norm)

    return (
        "❌ فرمت درست:\n"
        "• `100 دلار` یا `100 usd`\n"
        "• `50000 تومان دلار`\n"
        "• `20 ton` یا `1.5 btc` یا `100 pepe`\n"
        "• `1 btc eth` (تبدیل بین دو کریپتو)\n"
        "• `1000000 ریال تومان`\n"
        "• `50 تتر` یا `۲ بیتکوین`"
    )

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: finance_core_parts/part_016_profit_loss.py
# Auto-split part 16: profit_loss
def profit_loss(buy: float, sell: float, qty: float = 1.0) -> str:
    if buy <= 0:
        return "❌ قیمت خرید باید بزرگ‌تر از صفر باشد."
    gross = (sell - buy) * qty
    pct = (sell - buy) / buy * 100
    emoji = "📈" if gross >= 0 else "📉"
    status = "سود" if gross >= 0 else "ضرر"
    fee_est = (buy + sell) * qty * 0.005 / 2
    net = gross - fee_est
    return (
        f"{emoji} **محاسبه سود / ضرر**\n\n"
        f"قیمت خرید: {pn(f'{buy:,.0f}')}\n"
        f"قیمت فروش: {pn(f'{sell:,.0f}')}\n"
        f"تعداد / حجم: {pn(qty)}\n\n"
        f"**{status} ناخالص:** {pn(f'{abs(gross):,.0f}')}\n"
        f"**درصد:** {pct:+.2f}%\n"
        f"کارمزد تقریبی (۰.۵٪): {pn(f'{fee_est:,.0f}')}\n"
        f"**{status} تقریبی خالص:** {pn(f'{abs(net):,.0f}')}\n\n"
        f"{'✅ معامله در سود است.' if net >= 0 else '⚠️ معامله در ضرر است.'}"
    )

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: finance_core_parts/part_017_parse_profit.py
# Auto-split part 17: parse_profit
def parse_profit(text: str) -> tuple[float, float, float] | None:
    t = text.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
    nums = re.findall(r"[\d]+(?:\.\d+)?", t)
    nums = [float(n) for n in nums]
    if len(nums) >= 2:
        return nums[0], nums[1], nums[2] if len(nums) > 2 else 1.0
    return None

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: finance_core_parts/part_018_parse_currency_input.py
# Auto-split part 18: parse_currency_input
def parse_currency_input(text: str) -> tuple[float, str, str] | None:
    """پارس هوشمند: عدد + ارز مبدا + ارز مقصد (فارسی/انگلیسی)"""
    if not text:
        return None
    t = text.strip().translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
    t = t.replace("،", "").replace(",", "")
    t_lower = t.lower().replace("‌", " ").replace("  ", " ").strip()

    # الگوهای رایج
    # 1) 20 ton / 1.5 btc usdt / 100 دلار تومان
    m = re.match(
        r"^([\d.]+)\s*([a-zA-Zآ-ی]+)?\s*(?:به|to|=|→|->)?\s*([a-zA-Zآ-ی]+)?\s*$",
        t_lower,
    )
    if m:
        amount = float(m.group(1))
        a = (m.group(2) or "").strip()
        b = (m.group(3) or "").strip()
        # نرمال‌سازی فارسی
        a = _FA_CURRENCY.get(a, a)
        b = _FA_CURRENCY.get(b, b)
        return amount, a, b

    # 2) فقط عدد و یک کلمه چسبیده: 100دلار
    m2 = re.match(r"^([\d.]+)\s*([a-zA-Zآ-ی]+)\s*$", t_lower)
    if m2:
        amount = float(m2.group(1))
        a = _FA_CURRENCY.get(m2.group(2).strip(), m2.group(2).strip())
        return amount, a, ""

    return None

# END MERGED LEGACY PART: 
import asyncio
import re
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup
import httpx

from bot.logger import logger
from bot.utils.http_client import pooled_async_client, request_with_retry, safe_json

_cache = {}
_cache_t = {}
_cache_locks = {}

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}

TGJU_SLUGS = {
    "dollar": "price_dollar_rl", "euro": "price_eur", "pound": "price_gbp",
    "dirham": "price_aed", "lira": "price_try", "yuan": "price_cny",
    "ruble": "price_rub", "afghani": "price_afn", "dinar_iq": "price_iqd",
    "gold18": "geram18", "silver": "silver_999", "copper": "copper",
    "coin_emami": "sekee", "coin_bahar": "sekeb", "coin_half": "nim",
    "coin_quarter": "rob",
}
_AJAX_URLS = ("https://call1.tgju.org/ajax.json", "https://call2.tgju.org/ajax.json")
_BULK_CACHE_KEY = "tgju_bulk"
_BULK_TTL = 90

SYMBOL_TO_ID = {
    "btc": "bitcoin", "bitcoin": "bitcoin", "بیتکوین": "bitcoin", "بیت‌کوین": "bitcoin", "xbt": "bitcoin",
    "eth": "ethereum", "ethereum": "ethereum", "اتریوم": "ethereum",
    "usdt": "tether", "tether": "tether", "تتر": "tether",
    "usdc": "usd-coin", "busd": "binance-usd", "dai": "dai", "tusd": "true-usd", "fdusd": "first-digital-usd",
    "ton": "the-open-network", "toncoin": "the-open-network", "تون": "the-open-network",
    "bnb": "binancecoin", "sol": "solana", "xrp": "ripple", "ada": "cardano", "doge": "dogecoin",
    "dot": "polkadot", "matic": "matic-network", "polygon": "matic-network", "pol": "matic-network",
    "avax": "avalanche-2", "link": "chainlink", "trx": "tron", "shib": "shiba-inu",
    "ltc": "litecoin", "bch": "bitcoin-cash", "atom": "cosmos", "uni": "uniswap",
    "near": "near", "apt": "aptos", "arb": "arbitrum", "op": "optimism", "fil": "filecoin",
    "icp": "internet-computer", "vet": "vechain", "algo": "algorand", "xlm": "stellar",
    "eos": "eos", "xtz": "tezos", "aave": "aave", "mkr": "maker",
    "comp": "compound-governance-token", "snx": "havven", "crv": "curve-dao-token",
    "sushi": "sushi", "1inch": "1inch", "pepe": "pepe", "floki": "floki",
    "bonk": "bonk", "wif": "dogwifcoin", "sui": "sui", "sei": "sei-network",
    "inj": "injective-protocol", "tia": "celestia", "render": "render-token",
    "fet": "fetch-ai", "rndr": "render-token", "imx": "immutable-x", "gala": "gala",
    "sand": "the-sandbox", "mana": "decentraland", "axs": "axie-infinity",
    "theta": "theta-token", "ftm": "fantom", "hbar": "hedera-hashgraph",
    "egld": "elrond-erd-2", "kas": "kaspa", "rune": "thorchain", "stx": "blockstack",
    "ordi": "ordinals", "sats": "sats-ordinals",
    "wbtc": "wrapped-bitcoin", "steth": "staked-ether", "weeth": "wrapped-eeth",
    "leo": "leo-token", "okb": "okb", "cro": "crypto-com-chain", "mnt": "mantle",
    "tao": "bittensor", "ftt": "ftx-token", "bsv": "bitcoin-cash-sv",
    "etc": "ethereum-classic", "xmr": "monero", "zec": "zcash", "dash": "dash",
    "neo": "neo", "waves": "waves", "qtum": "qtum", "iota": "iota", "miota": "iota",
    "cake": "pancakeswap-token", "ldo": "lido-dao", "ens": "ethereum-name-service",
    "grt": "the-graph", "sand": "the-sandbox", "chz": "chiliz", "flow": "flow",
    "egld": "elrond-erd-2", "kava": "kava", "zil": "zilliqa", "bat": "basic-attention-token",
    "zrx": "0x", "enj": "enjincoin", "ankr": "ankr", "one": "harmony",
    "cfx": "conflux-token", "rose": "oasis-network", "ksm": "kusama",
    "twt": "trust-wallet-token", "gmx": "gmx", "dydx": "dydx-chain",
    "blur": "blur", "ape": "apecoin", "lrc": "loopring", "crv": "curve-dao-token",
    "jup": "jupiter-exchange-solana", "pyth": "pyth-network", "jto": "jito-governance-token",
    "wif": "dogwifcoin", "bome": "book-of-meme", "mew": "cat-in-a-dogs-world",
    "not": "notcoin", "dogs": "dogs-2", "hmstr": "hamster-kombat",
    "trump": "official-trump", "melania": "melania-meme", "pnut": "peanut-the-squirrel",
    "act": "act-i-the-ai-prophecy", "ai16z": "ai16z", "virtual": "virtual-protocol",
    "ondo": "ondo-finance", "ena": "ethena", "wld": "worldcoin-wld",
    "strk": "starknet", "zk": "zksync", "scroll": "scroll", "blast": "blast",
    "manta": "manta-network", "alt": "altlayer", "pendle": "pendle",
    "eigen": "eigenlayer", "ethfi": "ether-fi", "reth": "rocket-pool-eth",
    "arb": "arbitrum", "op": "optimism", "base": "base",
}

# نام‌های رایج فارسی برای ارز و کریپتو
_FA_CURRENCY = {
    "دلار": "usd", "دلارآمریکا": "usd", "usd": "usd", "dollar": "usd", "دلاری": "usd",
    "یورو": "eur", "euro": "eur", "eur": "eur",
    "پوند": "gbp", "pound": "gbp", "gbp": "gbp",
    "تومان": "toman", "تومن": "toman", "tmn": "toman",
    "ریال": "rial", "irr": "rial",
    "درهم": "aed", "aed": "aed",
    "لیر": "try", "try": "try",
    "یوان": "cny", "cny": "cny",
    "روبل": "rub", "rub": "rub",
    "بیتکوین": "btc", "بیت‌کوین": "btc", "بیت کوین": "btc", "بیتکویین": "btc",
    "bitcoin": "btc", "btc": "btc",
    "اتریوم": "eth", "ethereum": "eth", "eth": "eth",
    "تتر": "usdt", "tether": "usdt", "usdt": "usdt",
    "تون": "ton", "ton": "ton", "toncoin": "ton",
    "سولانا": "sol", "solana": "sol", "sol": "sol",
    "کاردانو": "ada", "ریپل": "xrp", "دوج": "doge", "دوج‌کوین": "doge", "دوجکوین": "doge",
}


