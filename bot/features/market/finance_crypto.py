"""Crypto-analysis orchestration extracted from finance.py."""
from __future__ import annotations
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

async def analyze_crypto(symbol: str, ai_summary: str = "", ai_guide: str = "", timeframe: str = "4h") -> str:
    """
    خلاصه کلی دقیقاً به سبک تحلیل‌گر حرفه‌ای:
    روند، حمایت/مقاومت، سیگنال، ستاپ، R:R، ریسک، وضعیت اجرا، جمع‌بندی AI، راهنما
    """
    symbol_clean = (symbol or "").lower().strip().replace(" ", "").replace("‌", "")
    if symbol_clean in ("gold", "xau", "xauusd", "xau/usd", "طلا", "طلای جهانی", "اونس", "اونس جهانی", "xauusd"):
        return await analyze_gold(timeframe)
    for junk in ("تحلیل", "analyze", "ارز", "کریپتو"):
        if symbol_clean.startswith(junk):
            symbol_clean = symbol_clean[len(junk):].strip()
    symbol_clean = symbol_clean.replace("usdt", "").strip() or "btc"

    # برای جلوگیری از تحلیل نمادهای تصادفی، تحلیل حرفه‌ای فقط روی دارایی شناخته‌شده اجرا می‌شود.
    supported = symbol_clean in SYMBOL_TO_ID or symbol_clean in {
        "bitcoin", "ethereum", "binancecoin", "solana", "ripple", "the-open-network",
        "dogecoin", "cardano", "tron", "chainlink", "litecoin", "polkadot", "avalanche-2",
        "shiba-inu", "matic-network", "near", "pepe", "sui", "aptos", "arbitrum", "optimism",
        "filecoin", "internet-computer", "vechain", "algorand", "stellar", "eos", "tezos",
        "aave", "maker", "curve-dao-token", "sushi", "1inch", "floki", "bonk", "dogwifcoin",
        "sei-network", "injective-protocol", "celestia", "render-token", "fetch-ai", "immutable-x",
        "gala", "the-sandbox", "decentraland", "axie-infinity", "theta-token", "fantom",
        "hedera-hashgraph", "elrond-erd-2", "kaspa", "thorchain", "blockstack", "ordinals", "sats-ordinals"
    }
    if not supported:
        return f"❌ نماد «{symbol_clean.upper()}» در فهرست تحلیل حرفه‌ای نیست. یک نماد معتبر مثل BTC، ETH، SOL یا XRP بفرستید."
    coin_id = await resolve_coin_id(symbol_clean)
    _sym_map = {
        "bitcoin": "BTC", "ethereum": "ETH", "binancecoin": "BNB", "solana": "SOL",
        "ripple": "XRP", "the-open-network": "TON", "dogecoin": "DOGE", "cardano": "ADA",
        "tron": "TRX", "chainlink": "LINK", "litecoin": "LTC", "polkadot": "DOT",
        "avalanche-2": "AVAX", "shiba-inu": "SHIB", "matic-network": "MATIC",
        "near": "NEAR", "pepe": "PEPE", "sui": "SUI",
    }
    pair = symbol_clean.upper().replace("USDT", "").replace("-", "") + "USDT"
    if coin_id and coin_id in _sym_map:
        pair = _sym_map[coin_id] + "USDT"
    base = pair.replace("USDT", "")

    async def _empty():
        return {}

    # تایم‌فریم تحلیل: 1h / 4h / 1d
    tf = (timeframe or "4h").lower().strip()
    if tf in ("1h", "h", "hour", "hourly", "ساعتی"):
        tf, tf_label, klimit = "1h", "ساعتی (1H)", 168
    elif tf in ("1d", "d", "day", "daily", "روزانه"):
        tf, tf_label, klimit = "1d", "روزانه (1D)", 120
    else:
        tf, tf_label, klimit = "4h", "میان‌مدت (4H)", 180

    detail_t = _fetch_coingecko_detail(coin_id) if coin_id else _empty()
    binance_t = _fetch_binance_futures(symbol_clean)
    fg_t = _fetch_fear_greed()
    klines_t = _fetch_klines_interval(pair, tf, klimit)
    fund_t = _fetch_fundamentals(coin_id, base)
    market_t = _f._fetch_market_context(base)

    detail, binance, fg, klines, fund, market = await __import__("asyncio").gather(
        detail_t, binance_t, fg_t, klines_t, fund_t, market_t
    )
    orderflow = await _fetch_orderflow_context(pair) if _fetch_orderflow_context else {}

    md = (detail.get("market_data") or {}) if isinstance(detail, dict) else {}
    current = md.get("current_price", {}).get("usd")
    chg_24 = md.get("price_change_percentage_24h")
    chg_7d = md.get("price_change_percentage_7d")

    if isinstance(fund, dict):
        current = current or fund.get("price")

    closes, highs, lows, vols, opens = [], [], [], [], []
    if klines:
        for k in klines:
            try:
                opens.append(float(k[1])); highs.append(float(k[2]))
                lows.append(float(k[3])); closes.append(float(k[4])); vols.append(float(k[5]))
            except Exception:
                continue
    if current is None and closes:
        current = closes[-1]

    ta = _compute_ta(closes, highs, lows, vols) if len(closes) >= 30 else {}
    if len(closes) >= 30:
        ta["atr"] = _atr(highs, lows, closes, 14)
        ta["patterns"] = _detect_candle_patterns(opens, highs, lows, closes)
    support, resistance = _support_resistance(closes, highs, lows, current)
    pa = _price_action_analysis(opens, highs, lows, closes, vols, support, resistance, ta.get("atr")) if len(closes) >= 30 else {}

    # سطوح حرفه‌ایِ خوشه‌ای؛ fallback به الگوریتم قدیمی اگر داده کم باشد
    levels = _advanced_levels(closes, highs, lows, current) if len(closes) >= 35 else {}
    if levels.get("supports"):
        support = levels["supports"][0]["price"]
    if levels.get("resistances"):
        resistance = levels["resistances"][0]["price"]

    # MTF موازی
    mtf = await _mtf_bundle(pair)
    # فیلتر ADX روزانه
    if mtf.get("force_wait"):
        ta["trend"] = "خنثی"
    # اگر تضاد شدید و تایم فعلی با روزانه مخالف
    primary_dir = (mtf.get("dirs") or {}).get(
        "1H" if tf == "1h" else ("1D" if tf == "1d" else "4H"), ""
    )
    daily_dir = (mtf.get("dirs") or {}).get("1D", "")
    if mtf.get("conflict") and primary_dir in ("صعودی", "نزولی") and daily_dir in ("صعودی", "نزولی") and primary_dir != daily_dir:
        # کاهش اطمینان
        pass

    trend = ta.get("trend", "خنثی")
    if mtf.get("force_wait"):
        trend = "خنثی"
    trend_arrow = {"صعودی": "صعودی ↗️", "نزولی": "نزولی ↘️", "خنثی": "خنثی ↔️"}.get(trend, "خنثی ↔️")
    signal, signal_emoji, setup_score, rr_quality, risk_level, exec_status = _derive_signal(
        ta, chg_24, binance or {}, current=current, support=support, resistance=resistance
    )
    # اجبار صبر اگر ADX روزانه ضعیف
    if mtf.get("force_wait"):
        signal, signal_emoji = "خنثی / احتیاط", "🟡"
        setup_score = min(setup_score, 5)
        exec_status = "صبر کنید ❌ — ADX روزانه ضعیف (بازار رنج)"
        risk_level = "متوسط 🟡"
    # امتیاز MTF این تایم
    tf_key = "1H" if tf == "1h" else ("1D" if tf == "1d" else "4H")
    if mtf.get("scores", {}).get(tf_key):
        setup_score = mtf["scores"][tf_key]

    # امتیاز حرفه‌ای در خروجی نهایی محاسبه می‌شود؛ نوع سیگنال «خرید/فروش» حفظ می‌شود.
    if "لانگ" in signal:
        signal_fa = f"خرید / لانگ {signal_emoji}"
    elif "شورت" in signal:
        signal_fa = f"فروش / شورت {signal_emoji}"
    else:
        signal_fa = f"{signal} {signal_emoji}"

    def fmt_p(v):
        if v is None:
            return "—"
        try:
            v = float(v)
        except Exception:
            return "—"
        if v >= 1000:
            return f"{v:,.2f}"
        if v >= 100:
            return f"{v:,.2f}"
        if v >= 1:
            return f"{v:,.2f}"
        return f"{v:,.4f}"

    # MFI تقریبی از حجم+قیمت برای متن جمع‌بندی
    mfi_note = ""
    rsi = ta.get("rsi")
    adx = ta.get("adx")
    if rsi is not None and rsi >= 60:
        mfi_note = "مومنتوم خرید نسبتاً قوی است."
    elif rsi is not None and rsi <= 40:
        mfi_note = "مومنتوم فروش غالب است."

    if not ai_summary:
        ai_summary, ai_guide = _build_smart_summary_pair(
            pair, trend, ta, support, resistance, signal, setup_score,
            chg_24, binance or {}, current, exec_status, mfi_note
        )
    if not ai_guide:
        ai_guide = _default_guide(signal, exec_status, support, resistance, current)

    # کوتاه‌سازی معقول
    if len(ai_summary) > 320:
        ai_summary = ai_summary[:320].rsplit(" ", 1)[0] + "…"
    if len(ai_guide) > 220:
        ai_guide = ai_guide[:220].rsplit(" ", 1)[0] + "…"

    # Telegram HTML: ساختار کوتاه و بخش‌بندی‌شده تا متن تحلیل روی موبایل شلوغ نشود.
    lines = [
        f"<b>📰 خلاصه کلی — {tf_label}</b>",
        "",
        f"🧭 <b>روند:</b> {trend_arrow}",
        f"🎯 <b>سیگنال:</b> {signal_fa}",
        f"⭐️ <b>کیفیت ستاپ:</b> {setup_score}.0/10",
        f"🔖 <b>وضعیت اجرا:</b> {exec_status}",
        "",
        "<b>📍 سطوح مهم</b>",
        f"🛡 حمایت: <code>{fmt_p(support)}</code>",
        f"🧱 مقاومت: <code>{fmt_p(resistance)}</code>",
        f"⚖️ ریوارد (R:R): {rr_quality}",
        f"⚠️ ریسک: {risk_level}",
        "",
        f"📝 <b>جمع‌بندی</b>\n{ai_summary}",
        f"ℹ️ <b>راهنما</b>\n{ai_guide}",
    ]
    if pa.get("valid"):
        classic_patterns = []
        for x in (pa.get("chart_patterns") or []):
            item = f"{x.get('name') or '—'} — {x.get('state') or '—'}"
            if x.get("bias"):
                item += f" | چشم‌انداز: {x.get('bias')}"
            if x.get("trigger") is not None:
                item += f" | تریگر: {fmt_p(x.get('trigger'))}"
            if x.get("target") is not None:
                item += f" | هدف: {fmt_p(x.get('target'))}"
            classic_patterns.append(item)

        classic_patterns_text = "\n".join(
            f"• {item}" for item in classic_patterns
        ) or "• الگوی قابل اتکا شناسایی نشد"

        lines += [
            "",
            "<b>🧠 تحلیل پرایس اکشن</b>",
            "",
            f"🏗 <b>ساختار:</b> {pa.get('structure','—')}",
            f"🔀 <b>BOS/CHOCH:</b> {pa.get('bos_choch') or 'ندارد'}",
            f"🕯 <b>کندل:</b> {', '.join(pa.get('patterns') or []) or 'سیگنال قوی ندارد'}",
            "",
            "<b>📐 الگوهای کلاسیک</b>",
            classic_patterns_text,
            "",
            f"💧 <b>نقدینگی:</b> {pa.get('liquidity_sweep') or 'Sweep مشخصی دیده نشد'}",
            f"⚖️ <b>Equal High/Low:</b> {fmt_p(pa.get('equal_highs')) if pa.get('equal_highs') else '—'} / {fmt_p(pa.get('equal_lows')) if pa.get('equal_lows') else '—'}",
            f"📍 <b>موقعیت قیمت:</b> {pa.get('location','—')}",
            f"💥 <b>شکست:</b> {pa.get('breakout') or 'تأیید نشده'}",
            f"📦 <b>حالت حرکت:</b> {pa.get('impulse_state') or 'نرمال'}",
            f"📊 <b>نسبت حجم:</b> {pa.get('volume_ratio'):.2f}x" if pa.get('volume_ratio') is not None else "📊 <b>نسبت حجم:</b> —",
        ]

    # چندتایم‌فریم + همگرایی
    lines.append("")
    lines.append("<b>⏱ امتیاز و همگرایی تایم‌فریم</b>")
    sc = mtf.get("scores") or {}
    di = mtf.get("dirs") or {}
    for k in ("15M", "1H", "4H", "1D", "1W"):
        s = sc.get(k)
        d = di.get(k, "—")
        arrow = {"صعودی": "↗️", "نزولی": "↘️", "رنج/ضعیف": "↔️"}.get(d, "·")
        lines.append(f"• {k}: {s if s is not None else '—'}/10 | {d} {arrow}")
    conv_txt, conv_pow = _mtf_convergence(mtf)
    lines.append(f"🔗 {conv_txt} | قدرت {conv_pow}/10")
    if mtf.get("force_wait"):
        try:
            lines.append(f"⚠️ ADX روزانه: {float(mtf.get('daily_adx') or 0):.0f} < 18 → فیلتر صبر فعال")
        except Exception:
            lines.append("⚠️ ADX روزانه ضعیف → فیلتر صبر فعال")
    if mtf.get("conflict"):
        lines.append("⚠️ تضاد تایم‌فریم‌ها — اولویت با روزانه / حجم کمتر")

    # ساختار بازار
    struct = _market_structure(highs, lows, closes) if len(closes) >= 20 else {}
    setattr(_f, "_ADAPT_SYMBOL", base)
    setattr(_f, "_ADAPT_SETUP", signal or "default")
    if current is not None:
        settle_signals(base, current)
    pro = _professional_score(ta, mtf, struct, {**(binance or {}), **(orderflow or {})}, fg, current, support, resistance, market)
    regime = (pro.get("regime") or {}).get("label") or _market_regime(ta, mtf, ta.get("vol_ratio"))
    gate = pro.get("quality_gate") or {}
    adaptive = pro.get("adaptive") or adaptive_profile(base, regime, signal or "default")
    alerts = alert_flags(current, support, resistance, ta, {**(binance or {}), **(orderflow or {})}, market)
    alerts = dedupe_alerts(alerts, key=f"{base}|{regime}")
    # Non-lookahead historical proxy scores for robustness metrics.
    hist_scores=[]
    if len(closes) >= 40:
        for i in range(len(closes)):
            if i < 30:
                hist_scores.append(50.0)
                continue
            fast=sum(closes[i-19:i])/20
            slow=sum(closes[i-49:i])/30 if i >= 49 else fast
            mom=(closes[i]/closes[i-12]-1)*100 if closes[i-12] else 0
            hist_scores.append(max(0,min(100,50+(20 if closes[i]>fast else -20)+(10 if fast>=slow else -10)+max(-10,min(10,mom*2)))))
    bt=backtest_directional(closes,hist_scores,horizon=6) if hist_scores else {"trades":0}
    wf=walk_forward(closes,hist_scores) if hist_scores else {"windows":0}
    calibrated_conf=calibration(pro["confidence"],bt.get("win_rate") if bt.get("trades",0)>=20 else None,bt.get("trades",0))
    entry=current
    stop=(current-(ta.get("atr") or 0)*1.5) if current is not None and "لانگ" in signal else (current+(ta.get("atr") or 0)*1.5) if current is not None and "شورت" in signal else None
    target=resistance if "لانگ" in signal else support if "شورت" in signal else None
    risk=risk_plan(entry,stop,target) if stop is not None and target is not None else {"valid":False}
    # Record only actionable long/short snapshots; outcomes are settled later from observed prices.
    if current is not None and gate.get("allowed") and ("لانگ" in signal or "شورت" in signal):
        record_signal(base, "long" if "لانگ" in signal else "short", current, stop, target, regime, pro.get("score",50), calibrated_conf, pro.get("factors",{}), horizon_seconds=21600, setup=signal or "default")
    lines.append("")
    lines.append("▎3. 🧠 امتیاز حرفه‌ای و وضعیت بازار")
    score_em = "🟢" if pro["score"] >= 60 else ("🔴" if pro["score"] <= 40 else "🟡")
    conf_em = "🟢" if pro["confidence"] >= 75 else ("🟡" if pro["confidence"] >= 55 else "🔴")
    lines.append(f"🎯 امتیاز جهت‌گیری: {pro['score']}/100 {score_em} | اطمینان داده: {calibrated_conf}% {conf_em}")
    lines.append(f"🌐 رژیم بازار: {regime}")
    lines.append(f"🛡 گیت کیفیت: {gate.get('label','—')}" + (f" | {', '.join(gate.get('reasons',[]))}" if gate.get('reasons') else ""))
    lines.append(f"🧠 یادگیری تطبیقی: {adaptive.get('samples',0)} نمونه | Win Rate {adaptive.get('win_rate','—')}% | وضعیت {'فعال' if adaptive.get('ready') else 'در حال جمع‌آوری داده'}")
    if adaptive.get("kill"):
        lines.append("🛑 Kill Switch تطبیقی: فعال — این ستاپ در این رژیم فعلاً تأیید نمی‌شود")
    if risk.get("valid"):
        lines.append(f"📐 مدیریت ریسک: R:R تقریبی {risk['rr']:.2f} | ریسک واحد {risk['risk_per_unit']:.4f}")
    if bt.get("trades",0):
        lines.append(f"🧪 بک‌تست بدون look-ahead: {bt['trades']} معامله | Win Rate {bt['win_rate']}% | PF {bt['profit_factor']} | بازده {bt['return_pct']}%")
    if wf.get("windows",0):
        lines.append(f"🔬 Walk-Forward OOS: {wf['windows']} پنجره | Win Rate {wf['out_of_sample']['win_rate']}%")
    if alerts:
        fa={"breakout_above_resistance":"شکست مقاومت","breakdown_below_support":"شکست حمایت","volume_spike":"جهش حجم","funding_extreme":"Funding افراطی","liquidation_activity":"فعالیت لیکوئیدیشن","news_sentiment_shift":"تغییر سنتیمنت اخبار"}
        lines.append("🚨 هشدارها: " + " | ".join(fa.get(x,x) for x in alerts))
    if orderflow:
        lines.append(f"🌊 Order Flow: {orderflow.get('imbalance_label','نامشخص')} | Large Trades: {orderflow.get('large_trade_bias','نامشخص')}")
    if levels.get("supports"):
        lines.append("🛡 حمایت‌ها: " + " | ".join(f"{x['price']:,.2f} ({x['strength']}/100)" for x in levels['supports'][:3]))
    if levels.get("resistances"):
        lines.append("🧱 مقاومت‌ها: " + " | ".join(f"{x['price']:,.2f} ({x['strength']}/100)" for x in levels['resistances'][:3]))
    lines.append(f"🧩 عوامل امتیاز: روند {pro['factors']['trend']:.0f} | مومنتوم {pro['factors']['momentum']:.0f} | حجم {pro['factors']['volume']:.0f} | ساختار {pro['factors']['structure']:.0f}")
    lines.append("⚙️ وزن پویا: " + " | ".join(f"{k} {v*100:.0f}%" for k,v in pro.get("weights",{}).items()))
    lines.append(f"📈 مشتقات: {'Funding ' + format(float(binance.get('funding_rate')), '+.3f') + '%' if binance.get('funding_rate') is not None else '—'} | Basis {float(binance.get('basis_pct') or 0):+.3f}%")
    if binance.get("liquidations_total") is not None:
        lines.append(f"💥 لیکوئیدیشن اخیر: کل {float(binance['liquidations_total']):,.0f} | لانگ {float(binance.get('liquidations_long') or 0):,.0f} | شورت {float(binance.get('liquidations_short') or 0):,.0f}")
    dom=market.get("btc_dominance")
    if dom is not None:
        lines.append(f"₿ BTC.D: {float(dom):.2f}% | ETH/BTC: {float(market.get('eth_btc') or 0):.6f}")
    if market.get("total2_market_cap_usd") is not None:
        lines.append(f"🌐 TOTAL2: ${float(market['total2_market_cap_usd'])/1e9:,.1f}B | TOTAL3: ${float(market.get('total3_market_cap_usd') or 0)/1e9:,.1f}B | Altseason: {market.get('altseason_proxy','نامشخص')}")
    macro=market.get("macro") or {}
    macro_bits=[]
    for k,label in (("DXY","DXY"),("GOLD","Gold"),("NASDAQ","Nasdaq"),("SPX","S&P500"),("US10Y","US10Y")):
        v=macro.get(k) or {}
        if v.get("price") is not None: macro_bits.append(f"{label} {float(v['change_pct'] or 0):+.2f}%")
    if macro_bits: lines.append("🌍 ماکرو: " + " | ".join(macro_bits))
    cor=market.get("correlations") or {}
    if cor:
        lines.append("🔗 همبستگی 30روزه با BTC: " + " | ".join(f"{k} {float(v):+.2f}" for k,v in cor.items()))
    news=market.get("news") or {}
    lines.append(f"📰 Sentiment اخبار: {news.get('label','نامشخص')} | تیترهای بررسی‌شده: {news.get('count',0)}")
    lines.append(f"🧪 کیفیت داده: {market.get('data_quality',0)}%")
    lines.append("")
    lines.append("▎4. 📊 ساختار و حجم")
    if struct:
        lines.append(f"ساختار: {struct.get('structure', '—')}")
        if struct.get("bos"):
            lines.append(f"BOS/CHOCH: {struct['bos']}")
    vol_note = _volume_breakout(closes, vols, resistance, support)
    if vol_note:
        lines.append(f"حجم: {vol_note}")
    div = _rsi_divergence(closes) if closes else None
    if div:
        lines.append(f"RSI: {div}")

    demand, supply = _demand_supply_zone(highs, lows, closes) if len(closes) >= 30 else (None, None)
    if demand:
        lines.append(f"ناحیه تقاضا: {fmt_p(demand[0])} – {fmt_p(demand[1])}")
    if supply:
        lines.append(f"ناحیه عرضه: {fmt_p(supply[0])} – {fmt_p(supply[1])}")

    pats = list(ta.get("patterns") or [])
    pats += list((mtf.get("1d") or {}).get("patterns") or [])
    pats = list(dict.fromkeys(pats))
    if pats:
        lines.append("")
        lines.append("▎5. 🕯 الگوهای کندلی")
        for p in pats[:4]:
            lines.append(f"• {p}")

    atr_v = ta.get("atr")
    if atr_v is not None:
        lines.append(f"📐 ATR(14): {atr_v:,.4f}" if atr_v < 10 else f"📐 ATR(14): {atr_v:,.2f}")

    # سناریوها
    lines.append("")
    lines.append("▎6. 🎲 سناریوها")
    for scn in _scenarios(signal, support, resistance, current, atr_v):
        lines.append(f"• {scn}")

    lines.append("")
    lines.extend(_format_fear_greed(fg))
    ls_lines = _format_long_short(binance or {})
    if ls_lines:
        lines.append("")
        lines.append("▎7. 📊 نسبت لانگ / شورت")
        lines.extend(ls_lines)
    lines.append(_signal_track_stub())

    if current is not None:
        lines.append("")
        lines.append(f"💵 قیمت لحظه‌ای: ${fmt_p(current)}")
        bits = []
        if chg_24 is not None:
            bits.append(f"۲۴س {'🟢' if chg_24>=0 else '🔴'}{chg_24:+.1f}%")
        if chg_7d is not None:
            bits.append(f"۷ر {'🟢' if chg_7d>=0 else '🔴'}{chg_7d:+.1f}%")
        if rsi is not None:
            bits.append(f"RSI {rsi:.0f}")
        if adx is not None:
            bits.append(f"ADX {adx:.0f}")
        if binance and binance.get("funding_rate") is not None:
            bits.append(f"Fund {binance['funding_rate']:+.3f}%")
        if fg:
            bits.append(f"F&G {fg.get('value')}")
        if bits:
            lines.append(" · ".join(bits))

    lines.append("")
    lines.append("⚠️ صرفاً تحلیلی/آموزشی است؛ توصیه سرمایه‌گذاری قطعی نیست.")
    text_out = chr(10).join(lines)
    if len(text_out) > 3900:
        text_out = text_out[:3890].rsplit(chr(10), 1)[0] + chr(10) + "…"
    return text_out


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
        parts.append("ADX قدرت روند را تأیید می‌کند.")
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
    """Render a direct XAU/USD candlestick chart for the requested timeframe.
    This never substitutes PAXG for the chart; if native XAU candles are unavailable,
    it returns None so the UI does not mislabel another instrument as XAU/USD.
    """
    tf = (timeframe or "1h").lower().strip()
    aliases = {"15m":"15m", "m15":"15m", "1h":"1h", "h":"1h", "4h":"4h", "h4":"4h", "1d":"1d", "d":"1d"}
    tf = aliases.get(tf, "1h")
    cfg = {"15m": ("15m", "3d", 288), "1h": ("1h", "14d", 168), "4h": ("4h", "45d", 180), "1d": ("1d", "180d", 120)}
    interval, range_, limit = cfg[tf]
    try:
        r = await _request_with_retry("GET", "https://xaus.com/api/v1/chart", retries=0,
                                      params={"symbol":"xau", "range":range_, "interval":interval})
        if getattr(r, "status_code", 0) != 200:
            d = {}
        else:
            d = safe_json(r) or {}
        rows = d.get("data") or d.get("series") or d.get("candles") or []
        parsed=[]
        for x in rows:
            try:
                if isinstance(x, dict):
                    ts=x.get("timestamp") or x.get("time") or x.get("t")
                    o=x.get("open") or x.get("o"); h=x.get("high") or x.get("h")
                    l=x.get("low") or x.get("l"); c=x.get("close") or x.get("c")
                else:
                    ts,o,h,l,c=x[:5]
                if None not in (ts,o,h,l,c): parsed.append((float(ts),float(o),float(h),float(l),float(c)))
            except Exception:
                continue
        if len(parsed) < 30:
            proxy = await _fetch_klines_interval("PAXGUSDT", interval, limit)
            if proxy and len(proxy) >= 30:
                parsed=[]
                for x in proxy:
                    try:
                        if len(x) >= 5:
                            parsed.append((float(x[0]),float(x[1]),float(x[2]),float(x[3]),float(x[4])))
                    except Exception:
                        continue
                proxy_mode = True
            else:
                return None, "XAU/USD chart data insufficient"
        else:
            proxy_mode = False
        ts=[x[0] for x in parsed[-8:]]
        diffs=[abs(ts[i]-ts[i-1]) for i in range(1,len(ts)) if ts[i] != ts[i-1]]
        med=sorted(diffs)[len(diffs)//2] if diffs else 0
        if med > 100000: med /= 1000
        target={"15m":900,"1h":3600,"4h":14400,"1d":86400}[tf]
        if diffs and not target*0.45 <= med <= target*1.8:
            return None, "XAU/USD provider returned a different interval"
        parsed=parsed[-limit:]
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle
        fig, ax = plt.subplots(figsize=(11,5.8), dpi=150)
        width = {"15m":0.62,"1h":0.62,"4h":0.60,"1d":0.55}[tf]
        for i,(_,o,h,l,c) in enumerate(parsed):
            ax.vlines(i,l,h,linewidth=0.9)
            bottom=min(o,c); height=max(abs(c-o), 0.0001)
            ax.add_patch(Rectangle((i-width/2,bottom),width,height,fill=False,linewidth=1.0))
        closes=[x[4] for x in parsed]
        if len(closes)>=20:
            ma=[]
            for i in range(len(closes)):
                w=closes[max(0,i-19):i+1]; ma.append(sum(w)/len(w))
            ax.plot(range(len(ma)),ma,linewidth=1.2,label="SMA20")
        ax.set_title(f"Gold / XAUUSD — {tf.upper()} | {'PAXG/USDT proxy' if proxy_mode else 'Direct XAU data'}")
        ax.set_ylabel("USD / oz")
        ax.grid(alpha=0.2)
        ax.legend(loc="upper left")
        ax.set_xlim(-1,len(parsed))
        fig.tight_layout()
        from io import BytesIO
        bio=BytesIO()
        fig.savefig(bio,format="png",bbox_inches="tight")
        plt.close(fig)
        bio.seek(0)
        return bio.getvalue(), f"Gold / XAUUSD {tf.upper()}"
    except Exception as exc:
        logger.debug("gold chart failed: %s", exc)
        return None, "XAU/USD chart unavailable"

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

