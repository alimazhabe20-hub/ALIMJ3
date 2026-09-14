# Auto-split part 4: analyze_crypto
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
    # امتیاز MTF این تایم؛ فیلتر صبر باید بعد از دریافت امتیاز اعمال شود،
    # وگرنه مثلاً امتیاز 9/10 دوباره جایگزین سقف 5/10 می‌شود.
    tf_key = "1H" if tf == "1h" else ("1D" if tf == "1d" else "4H")
    mtf_setup_score = mtf.get("scores", {}).get(tf_key)
    if mtf_setup_score is not None:
        setup_score = float(mtf_setup_score)
    if mtf.get("force_wait"):
        setup_score = min(float(setup_score), 5.0)

    # امتیاز حرفه‌ای در خروجی نهایی محاسبه می‌شود؛ نوع سیگنال «خرید/فروش» حفظ می‌شود.
    if "لانگ" in signal:
        signal_fa = f"خرید / لانگ {signal_emoji}"
    elif "شورت" in signal:
        signal_fa = f"فروش / شورت {signal_emoji}"
    else:
        signal_fa = f"{signal} {signal_emoji}"

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
        f"⭐️ <b>کیفیت ستاپ:</b> {float(setup_score):.1f}/10",
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
    if mtf.get("force_wait"):
        # ADX روزانه ضعیف، رژیم را برای نمایش به «رنج/احتیاط» تبدیل می‌کند
        # تا با سیگنال خنثی و وضعیت اجرای Wait تناقض نداشته باشد.
        regime = "رنج / نوسان کم (ADX روزانه ضعیف)"
    gate = pro.get("quality_gate") or {}
    if mtf.get("force_wait"):
        gate = {**gate, "label": "مجاز مشروط", "reasons": list(dict.fromkeys([*(gate.get("reasons") or []), "ADX روزانه ضعیف"]))}
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
