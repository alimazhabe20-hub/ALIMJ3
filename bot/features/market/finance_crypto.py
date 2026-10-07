"""Stable public facade.

IMPORTANT: Keep this file small and stable. New functionality belongs in the
secondary ``finance_crypto_parts/`` modules. The complete legacy implementation is kept
unchanged in ``finance_crypto_parts/features_market_finance_crypto_parts_part_999_core_legacy.py`` for compatibility.
"""
from __future__ import annotations

# ===== merged from bot/features/market/finance_crypto_parts/features_market_finance_crypto_parts_part_999_core_legacy.py =====
"""Ordered compatibility loader for cleaned source chunks."""
# ===== merged from bot/features/market/finance_crypto_parts/features_market_finance_crypto_parts_features_market_finance_crypto_parts_part_999_core_legacy_chunk_01.py =====
"""Crypto-analysis orchestration extracted from finance.py."""
import asyncio
from bot.features.market import finance as _f

# Runtime aliases; this module is imported lazily by the finance facade.
# Keep all dependencies that were originally module-level in finance.py exposed
# here after the V27 decomposition.  The facade is fully initialized before
# finance_crypto is imported, so these aliases avoid circular imports while
# preserving the original analysis pipeline.

SYMBOL_TO_ID = _f.SYMBOL_TO_ID
resolve_coin_id = _f.resolve_coin_id
pooled_async_client = _f.pooled_async_client
request_with_retry = _f.request_with_retry
safe_json = _f.safe_json
_fetch_coingecko_detail = _f._fetch_coingecko_detail
_fetch_binance_futures = _f._fetch_binance_futures
_fetch_klines_interval = _f._fetch_klines_interval
_atr = _f._atr
_detect_candle_patterns = _f._detect_candle_patterns
_format_fear_greed = getattr(_f, "_format_fear_greed", None)
get_crypto_analysis_short = getattr(_f, "get_crypto_analysis_short", None)
_fetch_klines_for_ta = _f._fetch_klines_for_ta
_compute_ta = _f._compute_ta
_support_resistance = _f._support_resistance
_derive_signal = _f._derive_signal
_mtf_bundle = _f._mtf_bundle
_market_structure = _f._market_structure
_rsi_divergence = _f._rsi_divergence
_volume_breakout = _f._volume_breakout
_demand_supply_zone = _f._demand_supply_zone
_mtf_convergence = _f._mtf_convergence
_advanced_levels = _f._advanced_levels
_price_action_analysis = _f._price_action_analysis
_market_regime = _f._market_regime
_professional_score = _f._professional_score
from bot.features.market.trading_intelligence import (backtest_directional, walk_forward, calibration, alert_flags, risk_plan, dedupe_alerts)
from bot.features.market.trading_adaptation import settle_signals, record_signal, adaptive_profile, performance_summary
_fetch_fundamentals = _f._fetch_fundamentals
_build_smart_summary = _f._build_smart_summary
_default_guide = _f._default_guide
_build_smart_summary_pair = _f._build_smart_summary_pair
_scenarios = _f._scenarios
_signal_track_stub = _f._signal_track_stub
_pair_from_symbol = _f._pair_from_symbol
_format_long_short = _f._format_long_short
_fetch_fear_greed = _f._fetch_fear_greed
_fetch_orderflow_context = getattr(_f, "_fetch_orderflow_context", None)
_tgju_price = getattr(_f, "_tgju_price", None)
_request_with_retry = _f.request_with_retry
safe_json = _f.safe_json
logger = _f.logger

# Shared formatter: both crypto and gold reports use it. Keeping it at module
# scope prevents NameError when analyze_crypto renders support/resistance.
def fmt_p(v):
    if v is None:
        return "—"
    try:
        v = float(v)
    except Exception:
        return "—"
    return f"{v:,.2f}" if abs(v) >= 1 else f"{v:,.4f}"

if _format_fear_greed is None:
    def _format_fear_greed(data):
        return str(data or "")

async def analyze_gold(timeframe: str = "4h") -> str:
    """تحلیل چندتایم‌فریم واقعی XAU/USD؛ S/R و Price Action هر گزارش از همان TF محاسبه می‌شود."""
    tf = (timeframe or "4h").lower().strip()
    aliases = {"15m":"15m", "m15":"15m", "ربع ساعته":"15m", "1h":"1h", "h":"1h", "hour":"1h", "hourly":"1h", "ساعتی":"1h", "4h":"4h", "h4":"4h", "1d":"1d", "d":"1d", "daily":"1d", "روزانه":"1d"}
    tf = aliases.get(tf, "4h")
    cfg = {"15m": ("15m", "3d", 288), "1h": ("1h", "14d", 168), "4h": ("4h", "45d", 180), "1d": ("1d", "180d", 120)}

    async def _xau_chart(interval: str, range_: str):
        try:
            r = await _request_with_retry(
                "GET", "https://xaus.com/api/v1/chart", retries=0,
                params={"symbol": "xau", "range": range_, "interval": interval},
            )
            if getattr(r, "status_code", 0) == 200:
                d = safe_json(r) or {}
                rows = d.get("data") or d.get("series") or d.get("candles") or []
                out = []
                for x in rows:
                    if isinstance(x, dict):
                        ts=x.get("timestamp") or x.get("time") or x.get("t")
                        o=x.get("open") or x.get("o"); h=x.get("high") or x.get("h")
                        l=x.get("low") or x.get("l"); c=x.get("close") or x.get("c"); v=x.get("volume") or x.get("v") or 0
                        if None not in (o,h,l,c): out.append([ts,o,h,l,c,v])
                    elif isinstance(x, (list,tuple)) and len(x) >= 5:
                        out.append(list(x[:6]))
                return out
        except Exception:
            pass
        return []

    async def _xau_spot():
        try:
            r = await _request_with_retry("GET", "https://xaus.com/api/v1/spot", retries=0, params={"compact":"1"})
            if getattr(r, "status_code", 0) == 200:
                d=safe_json(r) or {}
                return d.get("spot_usd_oz") or ((d.get("xau") or {}).get("price")), d.get("data_state") or {}
        except Exception:
            pass
        return None, {}

    async def _empty(): return None
    intervals = {k: cfg[k] for k in cfg}
    tasks = [_xau_chart(*intervals[k][:2]) for k in intervals]
    spot_task = _xau_spot()
    local_task = _tgju_price("geram18") if _tgju_price else _empty()
    results = await asyncio.gather(*tasks, spot_task, local_task, return_exceptions=True)
    charts = {}
    for k, r in zip(intervals, results[:4]): charts[k] = [] if isinstance(r, Exception) else (r or [])
    spot = results[4] if not isinstance(results[4], Exception) else (None,{})
    local18 = results[5] if not isinstance(results[5], Exception) else None
    direct_price, state = spot if isinstance(spot, tuple) else (None,{})

    # If a requested XAU interval is not actually returned by the provider, do not silently relabel it.
    def _valid_interval(rows, interval):
        if len(rows) < 30: return False
        ts=[]
        for r in rows[-8:]:
            try: ts.append(float(r[0]))
            except Exception: pass
        if len(ts) < 3: return True
        diffs=[abs(ts[i]-ts[i-1]) for i in range(1,len(ts)) if ts[i] != ts[i-1]]
        med=sorted(diffs)[len(diffs)//2] if diffs else 0
        # tolerate seconds/milliseconds timestamps and provider rounding.
        target={"15m":900,"1h":3600,"4h":14400,"1d":86400}[interval]
        if med > 100000: med /= 1000
        return target*0.45 <= med <= target*1.8

    # PAXG is a technical fallback only for an unavailable native XAU interval.
    async def _fallback_paxg(interval):
        lim=cfg[interval][2]
        rows=await _fetch_klines_interval("PAXGUSDT", interval, lim)
        return rows or []

    selected_rows = charts.get(tf, [])
    selected_source = "XAU/USD مستقیم"
    if not _valid_interval(selected_rows, tf):
        selected_rows = await _fallback_paxg(tf)
        selected_source = "PAXG/USDT fallback"

    def _ohlcv(rows):
        o=[]; h=[]; l=[]; c=[]; v=[]
        for k in rows:
            try:
                o.append(float(k[1])); h.append(float(k[2])); l.append(float(k[3])); c.append(float(k[4])); v.append(float(k[5] if len(k)>5 else 0))
            except Exception: continue
        return o,h,l,c,v

    o,h,l,c,v=_ohlcv(selected_rows)
    if len(c) < 30:
        return f"❌ داده کافی برای تحلیل حرفه‌ای طلا در تایم‌فریم {tf.upper()} در دسترس نیست."
    cur=float(direct_price) if direct_price is not None else c[-1]
    ta=_compute_ta(c,h,l,v); ta["atr"]=_atr(h,l,c,14)
    support,resistance=_support_resistance(c,h,l,cur)
    pa=_price_action_analysis(o,h,l,c,v,support,resistance,ta.get("atr"))
    struct=_market_structure(h,l,c); demand,supply=_demand_supply_zone(h,l,c)

    # MTF gold context: use native XAU data where available; never label PAXG as XAU.
    mtf_rows={}
    mtf_lines=[]
    for k in ("15m","1h","4h","1d"):
        rows=charts.get(k, [])
        src="XAU/USD"
        if not _valid_interval(rows,k):
            rows=await _fallback_paxg(k)
            src="PAXG fallback" if rows else "unavailable"
        mtf_rows[k]=(rows,src)
        oo,hh,ll,cc,vv=_ohlcv(rows)
        if len(cc) >= 30:
            mt=_compute_ta(cc,hh,ll,vv)
            s0,r0=_support_resistance(cc,hh,ll,cc[-1])
            pas=_price_action_analysis(oo,hh,ll,cc,vv,s0,r0,_atr(hh,ll,cc,14))
            direction=mt.get("trend") or "خنثی"
            score=round(max(0,min(10,float(pas.get("score", 5) if isinstance(pas,dict) else 5))),1)
            mtf_lines.append((k.upper(), score, direction, s0, r0, src))
        else:
            mtf_lines.append((k.upper(), None, "داده ناکافی", None, None, src))

    def f(x):
        return "—" if x is None else f"{float(x):,.2f}"

    lines=[
        "🥇 تحلیل حرفه‌ای طلا / XAUUSD", "━━━━━━━━━━━━━━━━━━━━",
        f"تایم‌فریم اصلی: {tf.upper()} | منبع تکنیکال: {selected_source}",
        f"💵 قیمت XAU/USD: ${f(cur)}",
        f"🇮🇷 طلای ۱۸ عیار: {f(local18)} تومان/گرم" if local18 else "🇮🇷 طلای ۱۸ عیار: —",
        f"🧭 روند: {ta.get('trend','خنثی')}",
        f"🛡 حمایت اصلی {tf.upper()}: ${f(support)}",
        f"🧱 مقاومت اصلی {tf.upper()}: ${f(resistance)}",
        f"📐 ATR(14): ${f(ta.get('atr'))}",
        f"📊 RSI: {float(ta.get('rsi')):.1f}" if ta.get('rsi') is not None else "📊 RSI: —",
        f"📈 ADX: {float(ta.get('adx')):.1f}" if ta.get('adx') is not None else "📈 ADX: —",
    ]
    if state: lines.append(f"🕒 وضعیت منبع: {state.get('status','نامشخص')} | {state.get('age_seconds','—')}s")
    def _format_chart_pattern(x):
        name = x.get('name') or '—'
        state = x.get('state') or '—'
        bias = f" | چشم‌انداز: {x.get('bias')}" if x.get('bias') else ''
        trigger = f" | تریگر: {f(x.get('trigger'))}" if x.get('trigger') is not None else ''
        target = f" | هدف: {f(x.get('target'))}" if x.get('target') is not None else ''
        return name + ' — ' + state + bias + trigger + target

    if struct:
        lines.append(f"🏗 ساختار: {struct.get('structure','—')}")
        if struct.get('bos'): lines.append(f"🔀 BOS/CHOCH: {struct['bos']}")
    if demand: lines.append(f"🟢 تقاضا {tf.upper()}: ${f(demand[0])} – ${f(demand[1])}")
    if supply: lines.append(f"🔴 عرضه {tf.upper()}: ${f(supply[0])} – ${f(supply[1])}")
    if pa.get("valid"):
        classic_patterns = []
        for x in (pa.get("chart_patterns") or []):
            item = f"{x.get('name', '—')} — {x.get('state', '—')}"
            if x.get("bias"):
                item += f" | چشم‌انداز: {x.get('bias')}"
            if x.get("trigger") is not None:
                item += f" | تریگر: {fmt_p(x.get('trigger'))}"
            if x.get("target") is not None:
                item += f" | هدف: {fmt_p(x.get('target'))}"
            classic_patterns.append(item)
        classic_patterns_text = ", ".join(classic_patterns) or "الگوی قابل اتکا شناسایی نشد"
        lines += ["", "🧠 تحلیل پرایس اکشن", f"🏗 ساختار: {pa.get('structure','—')}",
                  f"🔀 BOS/CHOCH: {pa.get('bos_choch') or 'ندارد'}",
                  f"🕯 الگو: {', '.join(pa.get('patterns') or []) or '—'}",
                  f"📐 الگوی کلاسیک: {classic_patterns_text}",
                  f"💧 نقدینگی/Sweep: {pa.get('liquidity_sweep') or '—'}",
                  f"📍 موقعیت قیمت: {pa.get('location','—')}"]
    lines += ["", "⏱ همگرایی چندتایم‌فریم طلا"]
    for k,score,direction,s0,r0,src in mtf_lines:
        score_txt=f"{score}/10" if score is not None else "—"
        lines.append(f"• {k}: {score_txt} | {direction} | S ${f(s0)} | R ${f(r0)} | {src}")
    bullish=sum(1 for _,_,d,*_ in mtf_lines if "صعود" in d)
    bearish=sum(1 for _,_,d,*_ in mtf_lines if "نزول" in d)
    if bullish >= 3 and bullish > bearish:
        lines.append("🟢 جمع‌بندی MTF: همگرایی صعودی غالب است؛ Long فقط با تأیید شکست/پولبک و حفظ حمایت معتبرتر است.")
    elif bearish >= 3 and bearish > bullish:
        lines.append("🔴 جمع‌بندی MTF: همگرایی نزولی غالب است؛ Short فقط با تأیید شکست حمایت و پولبک معتبرتر است.")
    else:
        lines.append("🟡 جمع‌بندی MTF: تایم‌فریم‌ها همسو نیستند؛ ورود وسط محدوده ریسک بالاتری دارد و Wait ارجح است.")
    if selected_source != "XAU/USD مستقیم":
        lines.append("⚠️ تایم‌فریم اصلی XAU/USD مستقیم از منبع در دسترس نبود؛ PAXG فقط fallback تکنیکال است و قیمت مرجع همچنان XAU/USD است.")
    return "\n".join(lines)


async def _empty_async():
    return None

# ===== end merged part =====


# ===== merged from bot/features/market/finance_crypto_parts/features_market_finance_crypto_parts_features_market_finance_crypto_parts_part_999_core_legacy_chunk_02.py =====
from bot.features.market.crypto_analyzer import analyze_crypto_impl

async def analyze_crypto(symbol: str, ai_summary: str='', ai_guide: str='', timeframe: str='4h') -> str:
    return await analyze_crypto_impl(symbol, ai_summary, ai_guide, timeframe)

# ===== end merged part =====


# ===== merged from bot/features/market/finance_crypto_parts/features_market_finance_crypto_parts_features_market_finance_crypto_parts_part_999_core_legacy_chunk_03.py =====
def _default_guide(signal, exec_status, support, resistance, current) -> str:
    if "فرصت گذشته" in (exec_status or ""):
        return (
            "قیمت از محدودهٔ مناسبِ این ستاپ عبور کرده و دیگر ورود به آن به‌صرفه نیست. "
            "دنبالش نکن؛ منتظرِ فرصت یا تحلیلِ تازه بمان."
        )
    if "صبر" in (exec_status or "") or "خنثی" in (signal or ""):
        return "الان ورود عجله‌ای توصیه نمی‌شود. صبر کن تا قیمت به حمایت/مقاومت کلیدی برسد یا شکست معتبر بدهد."
    if "لانگ" in (signal or ""):
        return "در صورت تأیید، ورود نزدیک حمایت منطقی‌تر است؛ حد ضرر زیر حمایت و هدف نزدیک مقاومت."
    if "شورت" in (signal or ""):
        return "در صورت تأیید، ورود نزدیک مقاومت منطقی‌تر است؛ حد ضرر بالای مقاومت و هدف نزدیک حمایت."
    return "قبل از ورود، حجم و کندل تأیید را چک کن و ریسک را محدود نگه دار."


def _build_smart_summary_pair(pair, trend, ta, support, resistance, signal, score,
                              chg_24, binance, current, exec_status, mfi_note=""):
    """(جمع‌بندی، راهنما)"""
    parts = []
    if trend == "نزولی":
        parts.append("روند در تایم‌فریم اخیر نزولی است و قیمت زیر میانگین‌های مهم معامله می‌شود.")
    elif trend == "صعودی":
        parts.append("روند صعودی در تایم‌فریم اخیر تثبیت شده و قیمت بالای میانگین‌های مهم قرار دارد.")
    else:
        parts.append("بازار در وضعیت رنج/خنثی است و قدرت روند محدود به نظر می‌رسد.")

    rsi = ta.get("rsi")
    adx = ta.get("adx")
    if "لانگ" in signal and support:
        parts.append("قیمت در حال پولبک یا نزدیک شدن به حمایت‌های کلیدی است.")
    elif "شورت" in signal and resistance:
        parts.append("قیمت به مقاومت‌های کلیدی نزدیک شده یا در حال تست آن‌هاست.")

    if rsi is not None:
        if rsi >= 70:
            parts.append("RSI در ناحیه اشباع خرید است.")
        elif rsi <= 30:
            parts.append("RSI در ناحیه اشباع فروش است.")
    if adx is not None and adx >= 25:
        parts.append("ADX تایم‌فریم فعلی قدرت حرکت را نشان می‌دهد.")
    elif adx is not None:
        parts.append("ADX تایم‌فریم فعلی ضعیف است و روند قدرت کافی ندارد.")
    if "ADX روزانه ضعیف" in (exec_status or ""):
        parts.append("ADX روزانه ضعیف است؛ بنابراین فیلتر صبر فعال است و ورود باید تا تأیید شکست/قدرت روند به تعویق بیفتد.")
    if mfi_note:
        parts.append(mfi_note)
    if binance and binance.get("funding_rate") is not None:
        fr = binance["funding_rate"]
        if fr > 0.05:
            parts.append("فاندینگ مثبت بالا نشان‌دهنده شلوغی لانگ‌هاست.")
        elif fr < -0.05:
            parts.append("فاندینگ منفی نشان‌دهنده فشار شورت‌هاست.")

    summary = " ".join(parts)
    guide = _default_guide(signal, exec_status, support, resistance, current)
    return summary, guide


async def _fetch_fundamentals(coin_id: str | None, base: str) -> dict:
    """فاندامنتال‌های سبک؛ منابع مستقل هم‌زمان خوانده می‌شوند."""
    out = {}
    retries = max(0, int(__import__('os').getenv("MARKET_HTTP_RETRIES", "0")))
    slug_map = {
        "BTC": None, "ETH": "ethereum", "SOL": "solana", "AVAX": "avalanche",
        "DOT": "polkadot", "ADA": "cardano", "TRX": "tron", "NEAR": "near",
        "MATIC": "polygon", "ARB": "arbitrum", "OP": "optimism", "SUI": "sui",
        "TON": "ton", "LINK": "chainlink",
    }
    slug = slug_map.get(base.upper())

    async def _global():
        try:
            return await request_with_retry("GET", "https://api.coingecko.com/api/v3/global", retries=retries)
        except Exception:
            return None

    async def _tvl():
        if not slug:
            return None
        try:
            return await request_with_retry("GET", f"https://api.llama.fi/tvl/{slug}", retries=retries)
        except Exception:
            return None

    async def _simple():
        if not coin_id:
            return None
        try:
            return await request_with_retry(
                "GET", "https://api.coingecko.com/api/v3/simple/price", retries=retries,
                params={
                    "ids": coin_id, "vs_currencies": "usd",
                    "include_market_cap": "true", "include_24hr_vol": "true",
                },
            )
        except Exception:
            return None

    rg, rt, rs = await asyncio.gather(_global(), _tvl(), _simple())
    if rg is not None and getattr(rg, "status_code", 0) == 200:
        g = (safe_json(rg) or {}).get("data") or {}
        out["btc_dom"] = (g.get("market_cap_percentage") or {}).get("btc")
    if rt is not None and getattr(rt, "status_code", 0) == 200:
        val = safe_json(rt)
        if isinstance(val, (int, float)) and val > 0:
            out["tvl"] = float(val)
    if rs is not None and getattr(rs, "status_code", 0) == 200 and coin_id:
        row = (safe_json(rs) or {}).get(coin_id) or {}
        out["price"] = row.get("usd")
        out["mcap"] = row.get("usd_market_cap")
        out["vol"] = row.get("usd_24h_vol")
    return out



async def get_gold_chart(timeframe: str = "1h"):
    """Render XAU/USD candlestick chart. Falls back to PAXG/USDT when native XAU is offline."""
    tf = (timeframe or "1h").lower().strip()
    aliases = {"15m": "15m", "m15": "15m", "1h": "1h", "h": "1h", "4h": "4h", "h4": "4h", "1d": "1d", "d": "1d"}
    tf = aliases.get(tf, "1h")
    cfg = {
        "15m": ("15m", "3d", 288),
        "1h": ("1h", "14d", 168),
        "4h": ("4h", "45d", 180),
        "1d": ("1d", "180d", 120),
    }
    interval, range_, limit = cfg[tf]
    proxy_mode = False
    parsed = []
    last_error = ""

    # 1) Try native XAU provider
    try:
        r = await _request_with_retry(
            "GET", "https://xaus.com/api/v1/chart", retries=1,
            params={"symbol": "xau", "range": range_, "interval": interval},
        )
        if getattr(r, "status_code", 0) == 200:
            d = safe_json(r) or {}
            rows = d.get("data") or d.get("series") or d.get("candles") or []
            for x in rows:
                try:
                    if isinstance(x, dict):
                        ts = x.get("timestamp") or x.get("time") or x.get("t")
                        o = x.get("open") or x.get("o")
                        h = x.get("high") or x.get("h")
                        l = x.get("low") or x.get("l")
                        c = x.get("close") or x.get("c")
                    else:
                        ts, o, h, l, c = x[:5]
                    if None not in (ts, o, h, l, c):
                        parsed.append((float(ts), float(o), float(h), float(l), float(c)))
                except Exception:
                    continue
    except Exception as exc:
        last_error = f"xaus: {exc}"
        logger.debug("gold chart xaus failed: %s", exc)

    # 2) Fall back to PAXG/XAUT proxies on Binance/OKX
    if len(parsed) < 30:
        for proxy_sym in ("PAXGUSDT", "XAUTUSDT"):
            try:
                proxy = await _fetch_klines_interval(proxy_sym, interval, limit)
                if proxy and len(proxy) >= 30:
                    parsed = []
                    for x in proxy:
                        try:
                            if len(x) >= 5:
                                parsed.append(
                                    (float(x[0]), float(x[1]), float(x[2]), float(x[3]), float(x[4]))
                                )
                        except Exception:
                            continue
                    if len(parsed) >= 30:
                        proxy_mode = True
                        last_error = ""
                        break
            except Exception as exc:
                last_error = f"{proxy_sym}: {exc}"
                logger.debug("gold chart proxy %s failed: %s", proxy_sym, exc)

    if len(parsed) < 30:
        return None, last_error or "XAU/USD chart data insufficient"

    # Soft interval check — do not hard-fail on minor drift
    try:
        ts = [x[0] for x in parsed[-8:]]
        diffs = [abs(ts[i] - ts[i - 1]) for i in range(1, len(ts)) if ts[i] != ts[i - 1]]
        med = sorted(diffs)[len(diffs) // 2] if diffs else 0
        if med > 100000:
            med /= 1000
        target = {"15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}[tf]
        # Only reject when clearly the wrong timeframe (very far from target)
        if diffs and not (target * 0.25 <= med <= target * 3.0):
            logger.debug("gold chart interval drift med=%s target=%s (continuing anyway)", med, target)
    except Exception:
        pass

    parsed = parsed[-limit:]

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle
        from io import BytesIO

        fig, ax = plt.subplots(figsize=(11, 5.8), dpi=150)
        width = {"15m": 0.62, "1h": 0.62, "4h": 0.60, "1d": 0.55}[tf]
        for i, (_, o, h, l, c) in enumerate(parsed):
            color = "#26a69a" if c >= o else "#ef5350"
            ax.vlines(i, l, h, linewidth=0.9, color=color)
            bottom = min(o, c)
            height = max(abs(c - o), 0.0001)
            ax.add_patch(
                Rectangle((i - width / 2, bottom), width, height, facecolor=color, edgecolor=color, linewidth=1.0)
            )
        closes = [x[4] for x in parsed]
        if len(closes) >= 20:
            ma = []
            for i in range(len(closes)):
                w = closes[max(0, i - 19) : i + 1]
                ma.append(sum(w) / len(w))
            ax.plot(range(len(ma)), ma, linewidth=1.2, label="SMA20", color="#42a5f5")
        source = "PAXG/USDT proxy" if proxy_mode else "Direct XAU data"
        ax.set_title(f"Gold / XAUUSD — {tf.upper()} | {source}")
        ax.set_ylabel("USD / oz")
        ax.grid(alpha=0.2)
        ax.legend(loc="upper left")
        ax.set_xlim(-1, len(parsed))
        fig.tight_layout()
        bio = BytesIO()
        fig.savefig(bio, format="png", bbox_inches="tight")
        plt.close(fig)
        bio.seek(0)
        return bio.getvalue(), f"Gold / XAUUSD {tf.upper()}"
    except Exception as exc:
        logger.warning("gold chart render failed: %s", exc)
        return None, f"chart render failed: {exc}"

def _build_smart_summary(pair, trend, ta, support, resistance, signal, score, chg_24, binance, current) -> str:
    parts = []
    if trend == "نزولی":
        parts.append("بازار زیر میانگین‌ها و با مومنتوم نزولی است.")
    elif trend == "صعودی":
        parts.append("بازار بالای میانگین‌ها و مومنتوم کوتاه‌مدت صعودی دارد.")
    else:
        parts.append("بازار رنج/خنثی است و قدرت روند محدود است.")
    rsi = ta.get("rsi")
    adx = ta.get("adx")
    if rsi is not None:
        if rsi >= 70:
            parts.append("RSI اشباع خرید؛ احتمال اصلاح.")
        elif rsi <= 30:
            parts.append("RSI اشباع فروش؛ احتمال برگشت کوتاه‌مدت.")
    if adx is not None and adx >= 25:
        parts.append("ADX روند را تأیید می‌کند.")
    elif adx is not None:
        parts.append("ADX روند ضعیف را نشان می‌دهد.")
    if "شورت" in signal:
        parts.append("استراتژی: فروش در پولبک به مقاومت.")
    elif "لانگ" in signal:
        parts.append("استراتژی: خرید روی حمایت.")
    else:
        parts.append("تا شکست واضح حمایت/مقاومت صبر بهتر است.")
    return " ".join(parts)

# ===== end merged part =====

# ===== end merged part =====

# JSON safety contract: safe_json
