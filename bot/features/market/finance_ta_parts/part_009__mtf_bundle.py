# Auto-split part 9: _mtf_bundle
async def _mtf_bundle(pair: str) -> dict:
    """تحلیل موازی 1H / 4H / 1D + تضاد"""
    k1, k4, kd = await asyncio.gather(
        _fetch_klines_interval(pair, "1h", 120),
        _fetch_klines_interval(pair, "4h", 120),
        _fetch_klines_interval(pair, "1d", 120),
    )

    def pack(klines):
        opens, highs, lows, closes, vols = [], [], [], [], []
        for k in klines or []:
            try:
                opens.append(float(k[1])); highs.append(float(k[2]))
                lows.append(float(k[3])); closes.append(float(k[4]))
                vols.append(float(k[5]))
            except Exception:
                continue
        if len(closes) < 30:
            return {}, opens, highs, lows, closes
        ta = _compute_ta(closes, highs, lows, vols)
        ta["atr"] = _atr(highs, lows, closes, 14)
        ta["patterns"] = _detect_candle_patterns(opens, highs, lows, closes)
        score, direction, adx = _score_timeframe(ta)
        ta["tf_score"] = score
        ta["tf_dir"] = direction
        return ta, opens, highs, lows, closes

    t1, *_ = pack(k1)
    t4, *_ = pack(k4)
    td, o_d, h_d, l_d, c_d = pack(kd)

    dirs = {
        "1H": (t1 or {}).get("tf_dir", "—"),
        "4H": (t4 or {}).get("tf_dir", "—"),
        "1D": (td or {}).get("tf_dir", "—"),
    }
    scores = {
        "1H": (t1 or {}).get("tf_score"),
        "4H": (t4 or {}).get("tf_score"),
        "1D": (td or {}).get("tf_score"),
    }

    # تضاد
    conflict = False
    bull = sum(1 for d in dirs.values() if d == "صعودی")
    bear = sum(1 for d in dirs.values() if d == "نزولی")
    if bull >= 1 and bear >= 1:
        conflict = True

    daily_adx = (td or {}).get("adx") or 0
    force_wait = daily_adx < 18 if td else False

    return {
        "1h": t1 or {},
        "4h": t4 or {},
        "1d": td or {},
        "dirs": dirs,
        "scores": scores,
        "conflict": conflict,
        "force_wait": force_wait,
        "daily_adx": daily_adx,
        "daily_klines": (o_d, h_d, l_d, c_d),
    }
