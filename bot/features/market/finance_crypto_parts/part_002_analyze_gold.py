# Auto-split part 2: analyze_gold
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
