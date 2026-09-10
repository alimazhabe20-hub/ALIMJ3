"""Technical-analysis helpers extracted from finance.py.

This module keeps market calculation code focused and reduces the size of the
market facade. It lazily references runtime HTTP/logging dependencies from
finance.py after that module is initialized.
"""
from __future__ import annotations
import asyncio
from bot.features.market import finance as _f
from bot.logger import logger
from bot.utils.http_client import pooled_async_client, request_with_retry, safe_json
from bot.features.market.trading_intelligence import detect_regime, dynamic_weights, quality_gate
from bot.features.market.trading_adaptation import adaptive_weights, adapt_score, adaptive_profile, kill_switch

# Compatibility aliases preserved from the original finance.py implementation.
# finance_ta is loaded through the finance facade after it is initialized.
_fetch_klines_interval = _f._fetch_klines_interval

async def _fetch_klines_for_ta(pair: str, limit: int = 200) -> list:
    """OHLCV از Binance Vision برای تحلیل تکنیکال"""
    try:
        async with pooled_async_client() as c:
            r = await request_with_retry("GET", 
                "https://data-api.binance.vision/api/v3/klines",
                params={"symbol": pair, "interval": "1h", "limit": limit},
            )
            if r.status_code == 200:
                return safe_json(r) or []
            # OKX fallback
            okx = pair.replace("USDT", "-USDT")
            r2 = await request_with_retry("GET", 
                "https://www.okx.com/api/v5/market/candles",
                params={"instId": okx, "bar": "1H", "limit": str(min(limit, 300))},
            )
            if r2.status_code == 200:
                data = (safe_json(r2) or {}).get("data") or []
                # OKX newest first → reverse; map to binance-like
                out = []
                for row in reversed(data):
                    out.append([int(row[0]), row[1], row[2], row[3], row[4], row[5]])
                return out
    except Exception as e:
        logger.warning(f"klines ta: {e}")
    return []


def _sma(arr: list, n: int):
    if len(arr) < n:
        return None
    return sum(arr[-n:]) / n


def _rsi(closes: list, period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(-period, 0):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _adx_approx(highs: list, lows: list, closes: list, period: int = 14) -> float | None:
    """تقریب ساده ADX"""
    if len(closes) < period * 2:
        return None
    trs = []
    dms_p, dms_m = [], []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        trs.append(tr)
        up = highs[i] - highs[i - 1]
        dn = lows[i - 1] - lows[i]
        dms_p.append(up if up > dn and up > 0 else 0)
        dms_m.append(dn if dn > up and dn > 0 else 0)
    if len(trs) < period:
        return None
    atr = sum(trs[-period:]) / period
    if atr == 0:
        return 0.0
    di_p = 100 * (sum(dms_p[-period:]) / period) / atr
    di_m = 100 * (sum(dms_m[-period:]) / period) / atr
    denom = di_p + di_m
    if denom == 0:
        return 0.0
    dx = 100 * abs(di_p - di_m) / denom
    return dx


def _compute_ta(closes, highs, lows, vols) -> dict:
    out = {}
    out["sma20"] = _sma(closes, 20)
    out["sma50"] = _sma(closes, 50) if len(closes) >= 50 else _sma(closes, 30)
    out["rsi"] = _rsi(closes, 14)
    out["adx"] = _adx_approx(highs, lows, closes, 14)
    if vols and len(vols) >= 20:
        avg_vol = sum(vols[-20:]) / 20
        out["vol_ratio"] = (vols[-1] / avg_vol) if avg_vol else 1.0
    # روند
    sma20, sma50 = out.get("sma20"), out.get("sma50")
    price = closes[-1]
    if sma20 and sma50:
        if price > sma20 > sma50:
            out["trend"] = "صعودی"
        elif price < sma20 < sma50:
            out["trend"] = "نزولی"
        else:
            out["trend"] = "خنثی"
    elif sma20:
        out["trend"] = "صعودی" if price > sma20 else "نزولی"
    else:
        out["trend"] = "خنثی"
    # شیب اخیر
    if len(closes) >= 24:
        chg = (closes[-1] - closes[-24]) / closes[-24] * 100
        out["chg_24h_bar"] = chg
        if out["trend"] == "خنثی":
            if chg > 2:
                out["trend"] = "صعودی"
            elif chg < -2:
                out["trend"] = "نزولی"
    return out



def _atr(highs, lows, closes, period: int = 14) -> float | None:
    """Average True Range"""
    if len(closes) < period + 1:
        return None
    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    if len(trs) < period:
        return None
    return sum(trs[-period:]) / period


def _detect_candle_patterns(opens, highs, lows, closes) -> list:
    """تشخیص ساده Engulfing و Pin Bar روی آخرین کندل‌ها"""
    patterns = []
    n = len(closes)
    if n < 3 or len(opens) < n:
        return patterns
    o, h, l, c = opens[-1], highs[-1], lows[-1], closes[-1]
    po, ph, pl, pc = opens[-2], highs[-2], lows[-2], closes[-2]
    body = abs(c - o)
    range_ = max(h - l, 1e-12)
    upper = h - max(c, o)
    lower = min(c, o) - l
    prev_body = abs(pc - po)

    # Bullish Engulfing
    if pc < po and c > o and c >= po and o <= pc and body > prev_body * 0.9:
        patterns.append("پوششی صعودی (Bullish Engulfing) 🟢")
    # Bearish Engulfing
    if pc > po and c < o and c <= po and o >= pc and body > prev_body * 0.9:
        patterns.append("پوششی نزولی (Bearish Engulfing) 🔴")

    # Pin Bar / Hammer (سایه پایین بلند)
    if lower >= body * 2 and upper <= body * 0.5 and body / range_ < 0.35:
        if c >= o:
            patterns.append("پین‌بار صعودی / چکش 🟢")
        else:
            patterns.append("پین‌بار با بدنه منفی (احتیاط) 🟡")
    # Shooting Star (سایه بالا بلند)
    if upper >= body * 2 and lower <= body * 0.5 and body / range_ < 0.35:
        if c <= o:
            patterns.append("ستاره دنباله‌دار (Shooting Star) 🔴")
        else:
            patterns.append("پین‌بار معکوس (احتیاط) 🟡")

    return patterns


def _score_timeframe(ta: dict) -> tuple:
    """امتیاز 1-10 و جهت برای یک تایم‌فریم"""
    score = 5
    trend = ta.get("trend") or "خنثی"
    rsi = ta.get("rsi")
    adx = ta.get("adx") or 0
    direction = "خنثی"

    if trend == "صعودی":
        score += 2
        direction = "صعودی"
    elif trend == "نزولی":
        score += 2
        direction = "نزولی"

    if rsi is not None:
        if direction == "صعودی" and 40 <= rsi <= 68:
            score += 1
        elif direction == "نزولی" and 32 <= rsi <= 60:
            score += 1
        elif direction == "صعودی" and rsi >= 75:
            score -= 2
        elif direction == "نزولی" and rsi <= 25:
            score -= 2

    if adx >= 25:
        score += 1
    elif adx < 18:
        score -= 2
        direction = "رنج/ضعیف"

    # الگوها
    for p in ta.get("patterns") or []:
        if "صعودی" in p or "چکش" in p:
            if direction != "نزولی":
                score += 1
        if "نزولی" in p or "دنباله‌دار" in p:
            if direction != "صعودی":
                score += 1

    score = max(1, min(10, score))
    return score, direction, adx


async def _mtf_bundle(pair: str) -> dict:
    """تحلیل موازی 15M/1H/4H/1D/1W + تضاد و همگرایی."""
    specs=[("15M","15m"),("1H","1h"),("4H","4h"),("1D","1d"),("1W","1w")]
    ks=await asyncio.gather(*[_fetch_klines_interval(pair,iv,160) for _,iv in specs], return_exceptions=True)
    def pack(klines):
        if isinstance(klines,Exception): klines=[]
        o=[];h=[];l=[];c=[];v=[]
        for k in klines or []:
            try:o.append(float(k[1]));h.append(float(k[2]));l.append(float(k[3]));c.append(float(k[4]));v.append(float(k[5]))
            except Exception: continue
        if len(c)<30:return {},o,h,l,c
        ta=_compute_ta(c,h,l,v);ta["atr"]=_atr(h,l,c,14);ta["patterns"]=_detect_candle_patterns(o,h,l,c)
        sc,di,adx=_score_timeframe(ta);ta.update(tf_score=sc,tf_dir=di)
        return ta,o,h,l,c
    ps=[pack(k) for k in ks];tfs={n:ps[i][0] for i,(n,_) in enumerate(specs)}
    dirs={n:(tfs[n] or {}).get("tf_dir","—") for n,_ in specs};scores={n:(tfs[n] or {}).get("tf_score") for n,_ in specs}
    bull=sum(x=="صعودی" for x in dirs.values());bear=sum(x=="نزولی" for x in dirs.values())
    weights={"15M":.10,"1H":.15,"4H":.25,"1D":.30,"1W":.20}
    bias=sum(weights[n]*(1 if dirs[n]=="صعودی" else -1 if dirs[n]=="نزولی" else 0) for n in weights)
    daily_adx=(tfs.get("1D") or {}).get("adx") or 0
    return {"15m":tfs.get("15M",{}),"1h":tfs.get("1H",{}),"4h":tfs.get("4H",{}),"1d":tfs.get("1D",{}),"1w":tfs.get("1W",{}),"dirs":dirs,"scores":scores,"conflict":bull>0 and bear>0,"force_wait":bool(tfs.get("1D")) and daily_adx<18,"daily_adx":daily_adx,"bias":bias,"weekly":tfs.get("1W",{}),"daily_klines":ps[3][1:]}


def _market_structure(highs, lows, closes) -> dict:
    """ساختار ساده: HH/HL یا LH/LL + BOS تقریبی"""
    if len(closes) < 20:
        return {"structure": "نامشخص", "bos": None}
    # swing تقریبی روی 5 کندل
    def swings(arr, mode="high"):
        pts = []
        for i in range(2, len(arr) - 2):
            if mode == "high" and arr[i] == max(arr[i-2:i+3]):
                pts.append((i, arr[i]))
            if mode == "low" and arr[i] == min(arr[i-2:i+3]):
                pts.append((i, arr[i]))
        return pts[-4:]
    sh = swings(highs, "high")
    sl = swings(lows, "low")
    structure = "رنج"
    bos = None
    if len(sh) >= 2 and len(sl) >= 2:
        if sh[-1][1] > sh[-2][1] and sl[-1][1] > sl[-2][1]:
            structure = "صعودی (HH/HL)"
            if closes[-1] > sh[-1][1]:
                bos = "BOS صعودی — شکست سقف اخیر"
        elif sh[-1][1] < sh[-2][1] and sl[-1][1] < sl[-2][1]:
            structure = "نزولی (LH/LL)"
            if closes[-1] < sl[-1][1]:
                bos = "BOS نزولی — شکست کف اخیر"
        elif sh[-1][1] < sh[-2][1] and sl[-1][1] > sl[-2][1]:
            structure = "احتمال CHOCH / فشردگی"
            bos = "تغییر ساختار محتمل"
    return {"structure": structure, "bos": bos, "last_swing_high": sh[-1][1] if sh else None, "last_swing_low": sl[-1][1] if sl else None}


def _rsi_divergence(closes, period: int = 14) -> str | None:
    """واگرایی ساده RSI روی ۲۰ کندل آخر"""
    if len(closes) < period + 25:
        return None
    # RSI series rough
    rsis = []
    for end in range(period + 1, len(closes) + 1):
        r = _rsi(closes[:end], period)
        if r is not None:
            rsis.append(r)
    if len(rsis) < 20:
        return None
    c = closes[-20:]
    r = rsis[-20:]
    # سقف قیمت vs RSI
    i_px_hi = max(range(len(c)), key=lambda i: c[i])
    i_rsi_hi = max(range(len(r)), key=lambda i: r[i])
    i_px_lo = min(range(len(c)), key=lambda i: c[i])
    i_rsi_lo = min(range(len(r)), key=lambda i: r[i])
    # bearish div: price higher high near end, rsi lower high
    if i_px_hi >= 12 and c[i_px_hi] >= max(c[:10]) and r[i_px_hi] < max(r[:10]) - 3:
        return "واگرایی نزولی RSI — ضعف در سقف"
    if i_px_lo >= 12 and c[i_px_lo] <= min(c[:10]) and r[i_px_lo] > min(r[:10]) + 3:
        return "واگرایی صعودی RSI — ضعف فروش در کف"
    return None


def _volume_breakout(closes, vols, resistance, support) -> str | None:
    if not closes or not vols or len(vols) < 20:
        return None
    avg = sum(vols[-20:]) / 20
    last_v = vols[-1]
    last_c = closes[-1]
    ratio = last_v / avg if avg else 1
    if resistance and last_c > resistance * 0.998 and ratio >= 1.4:
        return f"شکست مقاومت با حجم قوی (×{ratio:.1f})"
    if support and last_c < support * 1.002 and ratio >= 1.4:
        return f"شکست حمایت با حجم قوی (×{ratio:.1f})"
    if ratio >= 1.8:
        return f"حجم غیرعادی ×{ratio:.1f} میانگین"
    if ratio < 0.6:
        return "حجم ضعیف — شکست‌ها کم‌اعتبارتر"
    return None


def _demand_supply_zone(highs, lows, closes) -> tuple:
    """بازه تقریبی تقاضا/عرضه از ۱۰–۳۰ کندل قبل"""
    if len(closes) < 30:
        return None, None
    seg_l = lows[-30:-5]
    seg_h = highs[-30:-5]
    if not seg_l or not seg_h:
        return None, None
    demand = (min(seg_l), sorted(seg_l)[max(0, len(seg_l)//4)])
    supply = (sorted(seg_h)[max(0, 3*len(seg_h)//4 - 1)], max(seg_h))
    return demand, supply


def _mtf_convergence(mtf: dict) -> tuple:
    dirs=mtf.get("dirs") or {}; scores=mtf.get("scores") or {}
    vals=[dirs.get(k) for k in ("15M","1H","4H","1D","1W")]
    bull=sum(d=="صعودی" for d in vals);bear=sum(d=="نزولی" for d in vals);valid=sum(d in ("صعودی","نزولی") for d in vals)
    if not valid:return "داده MTF ناکافی",0
    if bull==valid:return "همگرایی کامل صعودی",10
    if bear==valid:return "همگرایی کامل نزولی",10
    power=round(max(bull,bear)/valid*10)
    return ("تمایل صعودی با تضاد تایم‌فریم" if bull>bear else "تمایل نزولی با تضاد تایم‌فریم"),power


def _professional_score(ta, mtf=None, structure=None, binance=None, fg=None, current=None, support=None, resistance=None, market=None):
    """0-100 multi-factor score; missing data lowers confidence instead of inventing facts."""
    ta=ta or {};mtf=mtf or {};structure=structure or {};binance=binance or {};market=market or {}
    f={k:50.0 for k in ("trend","momentum","volume","structure","derivatives","sentiment","macro","market","onchain")}
    trend=ta.get("trend");f["trend"]=78 if trend=="صعودی" else 22 if trend=="نزولی" else 50
    rsi=ta.get("rsi");f["momentum"]=max(15,min(85,50+(float(rsi)-50)*1.4)) if rsi is not None else 50
    vr=ta.get("vol_ratio");f["volume"]=max(20,min(80,50+(float(vr)-1)*25)) if vr is not None else 50
    st=str(structure.get("structure","")).lower();f["structure"]=75 if "صعود" in st else 25 if "نزول" in st else 50
    fr=binance.get("funding_rate");f["derivatives"]=max(20,min(80,50-float(fr)*180)) if fr is not None else 50
    if fg and fg.get("value") is not None:f["sentiment"]=max(20,min(80,50+(float(fg["value"])-50)*.7))
    ns=float((market.get("news") or {}).get("score") or 0);f["sentiment"]=max(15,min(85,f["sentiment"]+ns*4))
    dxy=((market.get("macro") or {}).get("DXY") or {}).get("change_pct");f["macro"]=max(20,min(80,50-float(dxy)*12)) if dxy is not None else 50
    dom=market.get("btc_dominance");f["market"]=max(25,min(75,50+(float(dom)-50)*1.2)) if dom is not None else 50
    obi=binance.get("order_book_imbalance")
    if obi is not None:
        f["market"]=max(10,min(90,f["market"]+float(obi)*20))
    liq_long=float(binance.get("liquidations_long") or 0); liq_short=float(binance.get("liquidations_short") or 0)
    if liq_long or liq_short:
        # liquidation imbalance is a contrarian stress signal, not a directional guarantee
        f["derivatives"]=max(10,min(90,f["derivatives"]+(10 if liq_short>liq_long*1.5 else -10 if liq_long>liq_short*1.5 else 0)))
    f["trend"]=max(10,min(90,f["trend"]+float(mtf.get("bias") or 0)*20))
    onchain = market.get("onchain") or {}
    if onchain.get("available"):
        # Activity is used only as a real-data confidence/health signal; direction stays neutral
        # unless a source supplies a directional metric.
        activity = float(onchain.get("transactions_24h") or 0)
        f["onchain"] = 55.0 if activity > 0 else 50.0
        market["onchain_score"] = f["onchain"]
    regime=detect_regime(ta, mtf, ta.get("vol_ratio"))
    weights=dynamic_weights(regime)
    # Empirical adaptation is bounded and activates only after enough settled outcomes.
    symbol = str(getattr(_f, "_ADAPT_SYMBOL", "BTC"))
    setup = str(getattr(_f, "_ADAPT_SETUP", "default"))
    weights=adaptive_weights(weights, symbol, regime.get("label", ""), setup)
    score=round(sum(f[k]*weights[k] for k in weights))
    vals=[trend,rsi,vr,fr,fg,mtf.get("scores"),market.get("btc_dominance"),market.get("macro"),market.get("news"),market.get("onchain_score")]
    avail=sum(x is not None and x!={} for x in vals)
    confidence=min(96,max(35,45+avail*5-(12 if mtf.get("conflict") else 0)))
    gate=quality_gate(score, confidence, mtf, float(market.get("data_quality") or 100), regime)
    if not gate["allowed"]:
        confidence=min(confidence, 54)
    score, confidence, adaptive = adapt_score(score, confidence, symbol, regime.get("label", ""), setup)
    gate=quality_gate(score, confidence, mtf, float(market.get("data_quality") or 100), regime)
    blocked, kill_reason=kill_switch(adaptive, gate.get("allowed", True))
    if blocked:
        gate={**gate, "allowed":False, "label":"صبر / عدم‌تأیید", "reasons":list(gate.get("reasons",[]))+([kill_reason] if kill_reason else [])}
        confidence=min(confidence,54)
    return {"score":max(0,min(100,score)),"confidence":confidence,
            "direction":"صعودی" if score>=60 else "نزولی" if score<=40 else "خنثی",
            "factors":f,"weights":weights,"regime":regime,"quality_gate":gate,
            "adaptive":adaptive}

