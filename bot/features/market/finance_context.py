"""finance: context responsibilities."""
from .finance_common import *  # noqa: F401,F403
from . import finance_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


async def _fetch_coingecko_detail(coin_id: str) -> dict:
    key = f"cg-detail:{coin_id}"
    now = asyncio.get_running_loop().time()
    cached = _HTTP_DATA_CACHE.get(key)
    if cached is not None and now - _HTTP_DATA_CACHE_T.get(key, 0) < MARKET_CACHE_TTLS["fundamentals"]:
        return cached
    retries = max(0, int(__import__('os').getenv("MARKET_HTTP_RETRIES", "0")))
    try:
        async with pooled_async_client() as c:
            r = await request_with_retry("GET", 
                f"https://api.coingecko.com/api/v3/coins/{coin_id}", retries=retries,
                params={
                    "localization": "false",
                    "tickers": "false",
                    "market_data": "true",
                    "community_data": "false",
                    "developer_data": "false",
                },
            )
            if r.status_code == 200:
                data = safe_json(r) or {}
                _HTTP_DATA_CACHE[key] = data
                _HTTP_DATA_CACHE_T[key] = now
                _trim_http_data_cache()
                return data
    except Exception as e:
        logger.warning(f"cg detail: {e}")
    return {}

async def _fetch_onchain_context(base: str = "BTC") -> dict:
    """Real network-level on-chain stats from Blockchair; never fabricate missing values."""
    base = (base or "BTC").upper()
    chain_map = {
        "BTC": "bitcoin", "BCH": "bitcoin-cash", "LTC": "litecoin", "DOGE": "dogecoin",
        "DASH": "dash", "ADA": "cardano", "XRP": "ripple", "XLM": "stellar",
        "XMR": "monero", "XTZ": "tezos", "EOS": "eos", "ETH": "ethereum",
    }
    chain = chain_map.get(base)
    if not chain:
        return {"available": False, "reason": "no_supported_public_chain"}
    key = f"onchain:{chain}"
    now = asyncio.get_running_loop().time()
    cached = _HTTP_DATA_CACHE.get(key)
    if cached is not None and now - _HTTP_DATA_CACHE_T.get(key, 0) < MARKET_CACHE_TTLS["onchain"]:
        return dict(cached)
    retries = max(0, int(__import__('os').getenv("MARKET_HTTP_RETRIES", "0")))
    try:
        r = await request_with_retry("GET", f"https://api.blockchair.com/{chain}/stats", retries=retries, params={"limit": 1})
        if getattr(r, "status_code", 0) != 200:
            return {"available": False, "reason": f"http_{getattr(r, 'status_code', 0)}"}
        payload = safe_json(r) or {}
        d = payload.get("data") or {}
        out = {"available": bool(d), "source": "Blockchair", "chain": chain}
        for k in ("blocks", "transactions", "transactions_24h", "blocks_24h", "circulation",
                  "circulation_approximate", "volume_24h", "volume_24h_approximate",
                  "difficulty", "hashrate_24h", "nodes", "hodling_addresses", "best_block_height"):
            if d.get(k) is not None:
                out[k] = d.get(k)
        # Convert the most useful raw values to normalized scores only when real data exists.
        if d:
            activity = float(d.get("transactions_24h") or 0)
            out["activity_24h"] = activity
            if base == "BTC" and d.get("hashrate_24h") is not None:
                out["network_security"] = "فعال"
        _HTTP_DATA_CACHE[key] = dict(out); _HTTP_DATA_CACHE_T[key] = now; _trim_http_data_cache()
        return out
    except Exception as e:
        logger.warning(f"onchain context: {e}")
        return {"available": False, "reason": "request_failed"}

async def _fetch_orderflow_context(pair: str) -> dict:
    """Lightweight order-flow/large-trade intelligence from Binance public endpoints.
    Large-trade direction is a heuristic, explicitly labelled as such; it is not whale identity data.
    """
    pair=(pair or "BTCUSDT").upper()
    key=f"orderflow:{pair}"
    now=asyncio.get_running_loop().time()
    cached=_HTTP_DATA_CACHE.get(key)
    if cached is not None and now-_HTTP_DATA_CACHE_T.get(key,0)<MARKET_CACHE_TTLS["price"]:
        return dict(cached)
    out={"available":False,"source":"Binance public","large_trade_bias":"نامشخص"}
    retries=max(0,int(__import__('os').getenv("MARKET_HTTP_RETRIES","0")))
    try:
        async def get(url, params):
            try:
                r=await request_with_retry("GET",url,retries=retries,params=params,headers=HEADERS)
                return safe_json(r) if getattr(r,"status_code",0)==200 else None
            except Exception:
                return None
        depth, trades = await asyncio.gather(
            get("https://api.binance.com/api/v3/depth", {"symbol":pair,"limit":100}),
            get("https://api.binance.com/api/v3/aggTrades", {"symbol":pair,"limit":100}),
        )
        if depth:
            bids=sum(float(x[0])*float(x[1]) for x in (depth.get("bids") or []) if len(x)>=2)
            asks=sum(float(x[0])*float(x[1]) for x in (depth.get("asks") or []) if len(x)>=2)
            total=bids+asks
            if total:
                imb=(bids-asks)/total
                out.update(order_book_bid_notional=bids,order_book_ask_notional=asks,order_book_imbalance=imb,
                           imbalance_label="خرید غالب" if imb>=.15 else "فروش غالب" if imb<=-.15 else "متعادل")
        if trades:
            buy=sell=0.0; large_buy=large_sell=0.0; threshold=100000.0
            for t in trades:
                try:
                    notional=float(t.get("p",0))*float(t.get("q",0))
                    # isBuyerMaker=True means aggressive seller hit the bid.
                    if bool(t.get("m")):
                        sell+=notional
                        if notional>=threshold: large_sell+=notional
                    else:
                        buy+=notional
                        if notional>=threshold: large_buy+=notional
                except Exception: continue
            flow=buy-sell
            large=large_buy-large_sell
            out.update(trade_buy_notional=buy,trade_sell_notional=sell,trade_flow=flow,
                       large_trade_buy_notional=large_buy,large_trade_sell_notional=large_sell,
                       large_trade_flow=large,
                       large_trade_bias="خریدهای بزرگ غالب" if large>threshold else "فروش‌های بزرگ غالب" if large<-threshold else "متعادل")
        out["available"]=bool(depth or trades)
        _HTTP_DATA_CACHE[key]=dict(out);_HTTP_DATA_CACHE_T[key]=now;_trim_http_data_cache()
    except Exception as e:
        logger.warning(f"orderflow context: {e}")
    return out

async def _fetch_market_context(base: str = "BTC") -> dict:
    """Market-wide context: dominance, total caps, macro proxies and lightweight news sentiment."""
    key = "market_context:v2"
    now = asyncio.get_running_loop().time()
    cached = _HTTP_DATA_CACHE.get(key)
    if cached is not None and now - _HTTP_DATA_CACHE_T.get(key, 0) < MARKET_CACHE_TTLS["market_context"]:
        return dict(cached)
    out = {"sources": [], "news": {"label": "نامشخص", "score": 0, "count": 0}, "macro": {}}
    retries = max(0, int(__import__('os').getenv("MARKET_HTTP_RETRIES", "0")))

    async def get(url, params=None, headers=None):
        try:
            r = await request_with_retry("GET", url, retries=retries, params=params, headers=headers or HEADERS)
            return r if getattr(r, "status_code", 0) == 200 else None
        except Exception:
            return None

    # CoinGecko global: BTC dominance + TOTAL market caps.
    cg = await get("https://api.coingecko.com/api/v3/global")
    if cg:
        try:
            d = safe_json(cg) or {}
            md = d.get("data") or {}
            pct = md.get("market_cap_percentage") or {}
            total = md.get("total_market_cap") or {}
            out["btc_dominance"] = float(pct.get("btc")) if pct.get("btc") is not None else None
            out["eth_dominance"] = float(pct.get("eth")) if pct.get("eth") is not None else None
            out["total_market_cap_usd"] = float(total.get("usd")) if total.get("usd") is not None else None
            out["sources"].append("CoinGecko Global")
            # TOTAL2/TOTAL3 are derived transparently from the same global market-cap snapshot.
            try:
                rr = await get("https://api.coingecko.com/api/v3/coins/markets", {"vs_currency":"usd","ids":"bitcoin,ethereum","price_change_percentage":"7d"})
                if rr:
                    rows = safe_json(rr) or []
                    caps = {str(x.get("id")): float(x.get("market_cap") or 0) for x in rows}
                    out["btc_market_cap_usd"] = caps.get("bitcoin")
                    out["eth_market_cap_usd"] = caps.get("ethereum")
                    if out.get("total_market_cap_usd") is not None:
                        out["total2_market_cap_usd"] = out["total_market_cap_usd"] - (out.get("btc_market_cap_usd") or 0)
                        out["total3_market_cap_usd"] = out["total2_market_cap_usd"] - (out.get("eth_market_cap_usd") or 0)
                    out["btc_7d"] = next((float(x.get("price_change_percentage_7d_in_currency") or 0) for x in rows if x.get("id")=="bitcoin"), None)
                    out["eth_7d"] = next((float(x.get("price_change_percentage_7d_in_currency") or 0) for x in rows if x.get("id")=="ethereum"), None)
                    if out.get("eth_7d") is not None and out.get("btc_7d") is not None:
                        out["altseason_proxy"] = "فعال‌تر" if out["eth_7d"] > out["btc_7d"] + 2 else "ضعیف‌تر" if out["eth_7d"] < out["btc_7d"] - 2 else "خنثی"
            except Exception:
                pass
        except Exception:
            pass

    # Binance spot: ETH/BTC relationship and BTC/USDT reference.
    try:
        rows = await asyncio.gather(
            get("https://api.binance.com/api/v3/ticker/price", {"symbol": "ETHBTC"}),
            get("https://api.binance.com/api/v3/ticker/24hr", {"symbol": "BTCUSDT"}),
        )
        if rows[0]:
            out["eth_btc"] = float((safe_json(rows[0]) or {}).get("price") or 0) or None
        if rows[1]:
            d = safe_json(rows[1]) or {}
            out["btc_change_24h"] = float(d.get("priceChangePercent") or 0)
        if rows[0] or rows[1]:
            out["sources"].append("Binance Spot")
    except Exception:
        pass

    # Yahoo Finance chart endpoint, public market-data proxy for DXY, gold, Nasdaq, S&P and US10Y.
    symbols = {"DXY":"DX-Y.NYB", "GOLD":"GC=F", "NASDAQ":"^IXIC", "SPX":"^GSPC", "US10Y":"^TNX"}
    async def yahoo(name, ticker):
        r = await get(f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}", {"range":"30d", "interval":"1d"})
        if not r:
            return name, None
        try:
            d = safe_json(r) or {}
            result=((d.get("chart") or {}).get("result") or [None])[0]
            meta=(result or {}).get("meta") or {}
            price=meta.get("regularMarketPrice") or meta.get("previousClose")
            prev=meta.get("previousClose")
            chg=((float(price)-float(prev))/float(prev)*100) if price is not None and prev not in (None,0) else None
            series=((result.get("indicators") or {}).get("quote") or [{}])[0].get("close") or []
            return name, {"price": float(price) if price is not None else None, "change_pct": chg, "series":[float(x) for x in series if x is not None]}
        except Exception:
            return name, None
    try:
        macro_rows = await asyncio.gather(*[yahoo(n,t) for n,t in symbols.items()])
        for n,v in macro_rows:
            if v: out["macro"][n]=v
        if out["macro"]: out["sources"].append("Yahoo Finance")
        # 30-day return correlations versus BTC. Pearson is used only when enough observations exist.
        try:
            btc_r = await yahoo("BTCUSD", "BTC-USD")
            bser=(btc_r[1] or {}).get("series") or []
            def ret(a): return [(a[i]-a[i-1])/a[i-1] for i in range(1,len(a)) if a[i-1] not in (0,None) and a[i] is not None]
            br=ret(bser)
            import math
            for k,v in list(out["macro"].items()):
                ar=ret(v.get("series") or [])
                n=min(len(br),len(ar))
                if n>=8:
                    x=br[-n:];y=ar[-n:];mx=sum(x)/n;my=sum(y)/n
                    den=math.sqrt(sum((z-mx)**2 for z in x)*sum((z-my)**2 for z in y))
                    out.setdefault("correlations",{})[k]=round(sum((x[i]-mx)*(y[i]-my) for i in range(n))/den,2) if den else 0.0
        except Exception:
            pass
    except Exception:
        pass

    # Lightweight news sentiment from Google News RSS. It is explicitly labelled as headline sentiment.
    try:
        q = (base or "BTC").upper() + " crypto market"
        r = await get("https://news.google.com/rss/search", {"q": q, "hl":"en-US", "gl":"US", "ceid":"US:en"})
        if r:
            xml = r.text or ""
            soup = BeautifulSoup(xml, "xml")
            titles=[x.get_text(" ", strip=True) for x in soup.find_all("title")[1:16]]
            bull_words=("surge","rally","bullish","gain","gains","rise","rises","breakout","approval","inflow","record high","adoption","optimistic","soars")
            bear_words=("crash","drop","falls","fall","bearish","selloff","outflow","hack","ban","lawsuit","liquidation","fear","risk-off","plunge","slump")
            score=0
            for t in titles:
                lo=t.lower()
                score += sum(1 for w in bull_words if w in lo)
                score -= sum(1 for w in bear_words if w in lo)
            label="مثبت" if score>=3 else ("منفی" if score<=-3 else "خنثی")
            out["news"]={"label":label,"score":score,"count":len(titles),"headlines":titles[:8]}
            out["sources"].append("Google News RSS")
    except Exception:
        pass

    # Real on-chain stats (BTC/ETH and other supported chains). Missing providers remain unavailable.
    try:
        out["onchain"] = await _fetch_onchain_context(base)
        if out["onchain"].get("available"):
            out["sources"].append("Blockchair On-chain")
    except Exception:
        out["onchain"] = {"available": False, "reason": "unavailable"}

    out["data_quality"] = min(100, 35 + len(out["sources"])*10 + (15 if out.get("btc_dominance") is not None else 0) + (10 if out.get("macro") else 0) + (10 if (out.get("onchain") or {}).get("available") else 0))
    _HTTP_DATA_CACHE[key]=dict(out); _HTTP_DATA_CACHE_T[key]=now; _trim_http_data_cache()
    return out

async def _fetch_binance_futures(symbol: str) -> dict:
    """Funding/OI/volume + long/short ratios, fetched in parallel."""
    sym = (symbol or "").upper().replace("USDT", "").replace("-", "") + "USDT"
    key = f"futures:{sym}"
    now = asyncio.get_running_loop().time()
    cached = _HTTP_DATA_CACHE.get(key)
    if cached is not None and now - _HTTP_DATA_CACHE_T.get(key, 0) < MARKET_CACHE_TTLS["derivatives"]:
        return dict(cached)
    retries = max(0, int(__import__('os').getenv("MARKET_HTTP_RETRIES", "0")))
    out = {}
    try:
        urls = [
            ("premium", "https://fapi.binance.com/fapi/v1/premiumIndex", {"symbol": sym}),
            ("force", "https://fapi.binance.com/fapi/v1/allForceOrders", {"symbol": sym, "limit": 100}),
            ("oi", "https://fapi.binance.com/fapi/v1/openInterest", {"symbol": sym}),
            ("ticker", "https://fapi.binance.com/fapi/v1/ticker/24hr", {"symbol": sym}),
            ("global", "https://fapi.binance.com/futures/data/globalLongShortAccountRatio", {"symbol": sym, "period": "1h", "limit": 1}),
            ("top", "https://fapi.binance.com/futures/data/topLongShortAccountRatio", {"symbol": sym, "period": "1h", "limit": 1}),
            ("pos", "https://fapi.binance.com/futures/data/topLongShortPositionRatio", {"symbol": sym, "period": "1h", "limit": 1}),
        ]
        responses = await asyncio.gather(*[
            request_with_retry("GET", url, retries=retries, params=params)
            for _, url, params in urls
        ], return_exceptions=True)
        for (name, _, _), response in zip(urls, responses):
            if isinstance(response, Exception) or getattr(response, "status_code", 0) != 200:
                continue
            try:
                data = safe_json(response)
                if name == "premium":
                    out["funding_rate"] = float(data.get("lastFundingRate") or 0) * 100
                    out["mark_price"] = float(data.get("markPrice") or 0)
                    out["index_price"] = float(data.get("indexPrice") or 0)
                    if out.get("index_price"):
                        out["basis_pct"] = (out["mark_price"] - out["index_price"]) / out["index_price"] * 100
                elif name == "force":
                    arr = data or []
                    buy_notional = sum(float(x.get("origQty") or 0) * float(x.get("price") or 0) for x in arr if str(x.get("side")).upper() == "SELL")
                    sell_notional = sum(float(x.get("origQty") or 0) * float(x.get("price") or 0) for x in arr if str(x.get("side")).upper() == "BUY")
                    out["liquidations_total"] = buy_notional + sell_notional
                    out["liquidations_long"] = buy_notional
                    out["liquidations_short"] = sell_notional
                elif name == "oi":
                    out["open_interest"] = float(data.get("openInterest") or 0)
                elif name == "ticker":
                    out["volume_24h"] = float(data.get("quoteVolume") or 0)
                    out["price_change_pct"] = float(data.get("priceChangePercent") or 0)
                else:
                    arr = data or []
                    if arr:
                        row = arr[-1]
                        prefix = {"global": "ls_global", "top": "ls_top", "pos": "ls_pos"}[name]
                        out[f"{prefix}_ratio"] = float(row.get("longShortRatio") or 0)
                        out[f"{prefix}_long"] = float(row.get("longAccount") or 0) * 100
                        out[f"{prefix}_short"] = float(row.get("shortAccount") or 0) * 100
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"binance futures {sym}: {e}")

    # Fallback OKX long/short اگر Binance خالی/مسدود بود
    if out.get("ls_global_ratio") is None:
        try:
            base = sym.replace("USDT", "")
            async with pooled_async_client() as c:
                r = await request_with_retry("GET", 
                    "https://www.okx.com/api/v5/rubik/stat/contracts/long-short-account-ratio", retries=retries,
                    params={"ccy": base},
                )
                if r.status_code == 200:
                    arr = (safe_json(r) or {}).get("data") or []
                    if arr:
                        # [ts, ratio] — ratio = long/short
                        ratio = float(arr[0][1])
                        # long% = ratio/(1+ratio)*100
                        long_pct = ratio / (1 + ratio) * 100
                        short_pct = 100 - long_pct
                        out["ls_global_ratio"] = ratio
                        out["ls_global_long"] = long_pct
                        out["ls_global_short"] = short_pct
                        out["ls_source"] = "okx"
                r2 = await request_with_retry("GET", 
                    "https://www.okx.com/api/v5/rubik/stat/contracts/long-short-account-ratio-contract-top-trader", retries=retries,
                    params={"instId": f"{base}-USDT-SWAP"},
                )
                if r2.status_code == 200:
                    arr = (safe_json(r2) or {}).get("data") or []
                    if arr:
                        ratio = float(arr[0][1])
                        long_pct = ratio / (1 + ratio) * 100
                        short_pct = 100 - long_pct
                        out["ls_top_ratio"] = ratio
                        out["ls_top_long"] = long_pct
                        out["ls_top_short"] = short_pct
        except Exception as e:
            logger.warning(f"okx ls {sym}: {e}")
    if out:
        _HTTP_DATA_CACHE[key] = dict(out)
        _HTTP_DATA_CACHE_T[key] = now
        _trim_http_data_cache()
    return out

def _format_long_short(binance: dict) -> list:
    """خطوط فارسی نسبت لانگ/شورت"""
    if not binance:
        return []
    lines = []
    gl = binance.get("ls_global_long")
    gs = binance.get("ls_global_short")
    gr = binance.get("ls_global_ratio")
    if gl is not None and gs is not None:
        bias = "لانگ غالب 🟢" if gl > gs + 5 else ("شورت غالب 🔴" if gs > gl + 5 else "متعادل ⚪")
        lines.append(f"👥 حساب‌ها (عمومی): لانگ {gl:.1f}% | شورت {gs:.1f}% — {bias}")
        if gr:
            lines.append(f"   نسبت L/S: {gr:.3f}")
    tl = binance.get("ls_top_long")
    ts = binance.get("ls_top_short")
    tr = binance.get("ls_top_ratio")
    if tl is not None and ts is not None:
        bias = "لانگ غالب 🟢" if tl > ts + 5 else ("شورت غالب 🔴" if ts > tl + 5 else "متعادل ⚪")
        lines.append(f"🏆 تریدرهای برتر (حساب): لانگ {tl:.1f}% | شورت {ts:.1f}% — {bias}")
        if tr:
            lines.append(f"   نسبت L/S: {tr:.3f}")
    pl = binance.get("ls_pos_long")
    ps = binance.get("ls_pos_short")
    pr = binance.get("ls_pos_ratio")
    if pl is not None and ps is not None:
        bias = "لانگ غالب 🟢" if pl > ps + 5 else ("شورت غالب 🔴" if ps > pl + 5 else "متعادل ⚪")
        lines.append(f"📦 حجم پوزیشن برتر: لانگ {pl:.1f}% | شورت {ps:.1f}% — {bias}")
        if pr:
            lines.append(f"   نسبت L/S: {pr:.3f}")
    # تفسیر کوتاه
    if gl is not None and tl is not None:
        if gl > 60 and tl < 45:
            lines.append("⚠️ عموم لانگ شلوغ‌اند ولی برترها محتاط‌تر — احتیاط در لانگ")
        elif gs > 60 and ts < 45:
            lines.append("⚠️ عموم شورت شلوغ‌اند ولی برترها محتاط‌تر — احتیاط در شورت")
    return lines

async def _fetch_fear_greed(limit: int = 7):
    """شاخص ترس و طمع — امروز + میانگین چند روز"""
    key = f"fear-greed:{limit}"
    now = asyncio.get_running_loop().time()
    cached = _HTTP_DATA_CACHE.get(key)
    if cached is not None and now - _HTTP_DATA_CACHE_T.get(key, 0) < 60:
        return cached
    retries = max(0, int(__import__('os').getenv("MARKET_HTTP_RETRIES", "0")))
    try:
        async with pooled_async_client() as c:
            r = await request_with_retry("GET", "https://api.alternative.me/fng/", retries=retries, params={"limit": str(limit)})
            if r.status_code == 200:
                data = (safe_json(r) or {}).get("data") or []
                if not data:
                    return None
                today = data[0]
                vals = []
                for d in data:
                    try:
                        vals.append(int(d.get("value")))
                    except Exception:
                        pass
                out = {
                    "value": today.get("value"),
                    "value_classification": today.get("value_classification"),
                    "timestamp": today.get("timestamp"),
                    "history": data,
                    "avg_7": (sum(vals) / len(vals)) if vals else None,
                    "prev": int(data[1]["value"]) if len(data) > 1 else None,
                }
                _HTTP_DATA_CACHE[key] = out
                _HTTP_DATA_CACHE_T[key] = now
                _trim_http_data_cache()
                return out
    except Exception as e:
        logger.warning(f"fear greed: {e}")
    return None

def _format_fear_greed(fg) -> list:
    """خطوط فارسی کامل برای F&G"""
    if not fg:
        return ["😨 ترس و طمع: در دسترس نیست"]
    try:
        val = int(fg.get("value") or 0)
    except Exception:
        val = 0
    cls = (fg.get("value_classification") or "").strip()
    # نقشه فارسی + ایموجی
    if val <= 24:
        fa, em = "ترس شدید", "😱"
    elif val <= 44:
        fa, em = "ترس", "😨"
    elif val <= 55:
        fa, em = "خنثی", "😐"
    elif val <= 74:
        fa, em = "طمع", "😊"
    else:
        fa, em = "طمع شدید", "🤑"
    lines = [f"😨 شاخص ترس و طمع: {val}/100 — {fa} {em}"]
    if cls:
        lines.append(f"   طبقه انگلیسی: {cls}")
    prev = fg.get("prev")
    avg7 = fg.get("avg_7")
    if prev is not None:
        delta = val - int(prev)
        arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "→")
        lines.append(f"   تغییر روزانه: {arrow} {delta:+d}")
    if avg7 is not None:
        lines.append(f"   میانگین ۷روز: {avg7:.0f}")
    # تفسیر معاملاتی کوتاه
    if val <= 25:
        lines.append("   تفسیر: ترس افراطی — احتمال فرصت خرید میان‌مدت (نه سیگنال ورود فوری)")
    elif val >= 75:
        lines.append("   تفسیر: طمع افراطی — احتیاط در لانگ‌های جدید")
    return lines

async def _fetch_fundamentals(*args, **kwargs):
    from bot.features.market.finance_crypto import _fetch_fundamentals as _fn
    return await _fn(*args, **kwargs)
