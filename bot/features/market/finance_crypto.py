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
_market_regime = _f._market_regime
_professional_score = _f._professional_score
_fetch_fundamentals = _f._fetch_fundamentals
_build_smart_summary = _f._build_smart_summary
_default_guide = _f._default_guide
_build_smart_summary_pair = _f._build_smart_summary_pair
_scenarios = _f._scenarios
_signal_track_stub = _f._signal_track_stub
_pair_from_symbol = _f._pair_from_symbol
_format_long_short = _f._format_long_short
_fetch_fear_greed = _f._fetch_fear_greed
_tgju_price = getattr(_f, "_tgju_price", None)
_request_with_retry = _f.request_with_retry
safe_json = _f.safe_json
logger = _f.logger

if _format_fear_greed is None:
    def _format_fear_greed(data):
        return str(data or "")

async def analyze_gold(timeframe: str = "4h") -> str:
    """تحلیل طلا با XAU/USD spot واقعی + طلای ۱۸ عیار TGJU؛ PAXG فقط fallback تکنیکال است."""
    tf = (timeframe or "4h").lower().strip()
    if tf not in ("1h", "4h", "1d"):
        tf = "4h"
    limit = 168 if tf == "1h" else 180 if tf == "4h" else 120

    async def _xau_chart():
        try:
            r = await _request_with_retry("GET", "https://xaus.com/api/v1/chart", retries=0,
                                         params={"symbol": "xau", "range": "7d", "interval": "1h"})
            if getattr(r, "status_code", 0) == 200:
                d = safe_json(r) or {}
                rows = d.get("data") or d.get("series") or d.get("candles") or []
                out=[]
                for x in rows:
                    if isinstance(x, dict):
                        ts=x.get("timestamp") or x.get("time") or x.get("t")
                        o=x.get("open") or x.get("o"); h=x.get("high") or x.get("h")
                        l=x.get("low") or x.get("l"); c=x.get("close") or x.get("c"); v=x.get("volume") or x.get("v") or 0
                        if None not in (o,h,l,c): out.append([ts,o,h,l,c,v])
                    elif isinstance(x, (list,tuple)) and len(x)>=5:
                        out.append(list(x[:6]))
                return out
        except Exception:
            pass
        return []

    async def _xau_spot():
        try:
            r = await _request_with_retry("GET", "https://xaus.com/api/v1/spot", retries=0,
                                         params={"compact": "1"})
            if getattr(r, "status_code", 0) == 200:
                d=safe_json(r) or {}
                return d.get("spot_usd_oz") or ((d.get("xau") or {}).get("price")), d.get("data_state") or {}
        except Exception:
            pass
        return None, {}

    chart_task = _xau_chart()
    spot_task = _xau_spot()
    local_task = _tgju_price("geram18") if _tgju_price else _empty_async()
    chart, spot, local18 = await asyncio.gather(chart_task, spot_task, local_task, return_exceptions=True)
    if isinstance(chart, Exception): chart=[]
    if isinstance(spot, Exception): spot=(None,{})
    if isinstance(local18, Exception): local18=None
    direct_price, state = spot if isinstance(spot, tuple) else (None,{})

    # If the direct XAU chart is unavailable, use PAXG only as a technical fallback.
    pair = "XAU/USD"
    if chart and len(chart) >= 30:
        rows=chart[-limit:]
        opens=[]; highs=[]; lows=[]; closes=[]; vols=[]
        for k in rows:
            try:
                opens.append(float(k[1])); highs.append(float(k[2])); lows.append(float(k[3])); closes.append(float(k[4])); vols.append(float(k[5] if len(k)>5 else 0))
            except Exception: continue
        source_label="XAU/USD مستقیم"
    else:
        pair="PAXGUSDT"
        klines=await _fetch_klines_interval(pair, tf, limit)
        opens=[]; highs=[]; lows=[]; closes=[]; vols=[]
        for k in klines or []:
            try:
                opens.append(float(k[1])); highs.append(float(k[2])); lows.append(float(k[3])); closes.append(float(k[4])); vols.append(float(k[5]))
            except Exception: continue
        source_label="PAXG/USDT fallback"
    if len(closes) < 30:
        return "❌ داده کافی برای تحلیل حرفه‌ای طلا در دسترس نیست."
    cur = float(direct_price) if direct_price is not None else closes[-1]
    ta=_compute_ta(closes, highs, lows, vols); ta["atr"]=_atr(highs,lows,closes,14)
    support,resistance=_support_resistance(closes,highs,lows,cur)
    struct=_market_structure(highs,lows,closes); demand,supply=_demand_supply_zone(highs,lows,closes)
    mtf=await _mtf_bundle(pair)
    def f(v):
        return "—" if v is None else f"{float(v):,.2f}"
    lines=["🥇 تحلیل حرفه‌ای طلا","────────────────────",
           f"منبع جهانی: {source_label} | XAU/USD: ${f(cur)} | تایم‌فریم: {tf.upper()}",
           f"🇮🇷 طلای ۱۸ عیار: {f(local18)} تومان/گرم" if local18 else "🇮🇷 طلای ۱۸ عیار: —",
           f"🧭 روند: {ta.get('trend','خنثی')}",f"🛡 حمایت اصلی: ${f(support)}",f"🧱 مقاومت اصلی: ${f(resistance)}",
           f"📐 ATR(14): ${f(ta.get('atr'))}",f"📊 RSI: {float(ta.get('rsi')):.1f}" if ta.get('rsi') is not None else "📊 RSI: —",
           f"📈 ADX: {float(ta.get('adx')):.1f}" if ta.get('adx') is not None else "📈 ADX: —"]
    if state: lines.append(f"🕒 وضعیت منبع: {state.get('status','نامشخص')} | {state.get('age_seconds','—')}s")
    if struct:
        lines.append(f"🏗 ساختار: {struct.get('structure','—')}")
        if struct.get('bos'): lines.append(f"🔀 BOS/CHOCH: {struct['bos']}")
    if demand: lines.append(f"🟢 ناحیه تقاضا: ${f(demand[0])} – ${f(demand[1])}")
    if supply: lines.append(f"🔴 ناحیه عرضه: ${f(supply[0])} – ${f(supply[1])}")
    sc,di=mtf.get('scores') or {},mtf.get('dirs') or {}
    lines += ["","⏱ همگرایی تایم‌فریم‌ها:"]
    for k in ("15M","1H","4H","1D","1W"):
        lines.append(f"• {k}: {sc.get(k,'—')}/10 | {di.get(k,'—')}")
    if resistance and cur > resistance: lines.append("🟢 سناریو صعودی: تثبیت بالای مقاومت و تبدیل آن به حمایت، اعتبار حرکت را بیشتر می‌کند.")
    elif support and cur < support: lines.append("🔴 سناریو نزولی: بازپس‌گیری حمایت شرط مهم کاهش فشار فروش است.")
    else: lines.append("🟡 سناریو: واکنش قیمت به حمایت/مقاومت تعیین‌کننده است؛ ورود وسط محدوده کم‌کیفیت‌تر است.")
    if source_label != "XAU/USD مستقیم": lines.append("⚠️ منبع مستقیم XAU/USD در دسترس نبود؛ PAXG فقط به‌عنوان fallback تکنیکال استفاده شد.")
    return "\n".join(lines)


async def _empty_async():
    return None

async def analyze_crypto(symbol: str, ai_summary: str = "", ai_guide: str = "", timeframe: str = "4h") -> str:
    """
    خلاصه کلی دقیقاً به سبک تحلیل‌گر حرفه‌ای:
    روند، حمایت/مقاومت، سیگنال، ستاپ، R:R، ریسک، وضعیت اجرا، جمع‌بندی AI، راهنما
    """
    symbol_clean = (symbol or "").lower().strip().replace(" ", "").replace("‌", "")
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

    lines = [
        f"▎1. 📰 خلاصه کلی — {tf_label}",
        f"🧭 روند: {trend_arrow}",
        f"🛡 حمایت کلیدی: {fmt_p(support)}",
        f"🧱 مقاومت کلیدی: {fmt_p(resistance)}",
        f"🎯 نوع سیگنال: {signal_fa}",
        f"⭐️ امتیاز کیفیت ستاپ: {setup_score}.0",
        f"⚖️ کیفیت ریوارد (R:R وزنی): {rr_quality}",
        f"⚠️ سطح ریسک (حد ضرر): {risk_level}",
        f"🔖 وضعیت اجرا: {exec_status}",
        f"📝 جمع‌بندی: {ai_summary}",
        f"ℹ️ راهنما: {ai_guide}",
    ]

    # چندتایم‌فریم + همگرایی
    lines.append("")
    lines.append("▎2. ⏱ امتیاز و همگرایی تایم‌فریم")
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
    pro = _professional_score(ta, mtf, struct, binance or {}, fg, current, support, resistance, market)
    regime = _market_regime(ta, mtf, ta.get("vol_ratio"))
    lines.append("")
    lines.append("▎3. 🧠 امتیاز حرفه‌ای و وضعیت بازار")
    score_em = "🟢" if pro["score"] >= 60 else ("🔴" if pro["score"] <= 40 else "🟡")
    conf_em = "🟢" if pro["confidence"] >= 75 else ("🟡" if pro["confidence"] >= 55 else "🔴")
    lines.append(f"🎯 امتیاز جهت‌گیری: {pro['score']}/100 {score_em} | اطمینان داده: {pro['confidence']}% {conf_em}")
    lines.append(f"🌐 رژیم بازار: {regime}")
    if levels.get("supports"):
        lines.append("🛡 حمایت‌ها: " + " | ".join(f"{x['price']:,.2f} ({x['strength']}/100)" for x in levels['supports'][:3]))
    if levels.get("resistances"):
        lines.append("🧱 مقاومت‌ها: " + " | ".join(f"{x['price']:,.2f} ({x['strength']}/100)" for x in levels['resistances'][:3]))
    lines.append(f"🧩 عوامل امتیاز: روند {pro['factors']['trend']:.0f} | مومنتوم {pro['factors']['momentum']:.0f} | حجم {pro['factors']['volume']:.0f} | ساختار {pro['factors']['structure']:.0f}")
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

