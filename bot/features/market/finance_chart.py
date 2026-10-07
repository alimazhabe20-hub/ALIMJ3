"""finance: chart responsibilities."""
from .finance_common import *  # noqa: F401,F403
from . import finance_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


async def _cache_lock(key):
    lock = _cache_locks.get(key)
    if lock is None:
        lock = _cache_locks[key] = asyncio.Lock()
    return lock

async def get_crypto_chart(symbol: str, days: int = 7) -> Tuple[Optional[bytes], str]:
    """
    نمودار چندپنلی شبیه TradingView/AlgoAnalyzer:
    کندل + Bollinger + EMA + حجم + ADX + RSI
    """
    try:
        days = max(1, min(int(days or 7), 365))
    except Exception:
        days = 7

    symbol_clean = (symbol or "").lower().strip().replace(" ", "").replace("‌", "")
    for junk in ("نمودار", "chart", "قیمت", "روز", "روزه", "price", "تحلیل"):
        symbol_clean = symbol_clean.replace(junk, "")
    symbol_clean = symbol_clean.replace("usdt", "").strip() or "btc"

    coin_id = await resolve_coin_id(symbol_clean)
    _sym_map = {
        "bitcoin": "BTC", "ethereum": "ETH", "tether": "USDT", "binancecoin": "BNB",
        "solana": "SOL", "ripple": "XRP", "the-open-network": "TON", "dogecoin": "DOGE",
        "cardano": "ADA", "tron": "TRX", "chainlink": "LINK", "litecoin": "LTC",
        "polkadot": "DOT", "avalanche-2": "AVAX", "shiba-inu": "SHIB",
        "matic-network": "MATIC", "near": "NEAR", "pepe": "PEPE", "sui": "SUI",
    }
    pair = symbol_clean.upper().replace("USDT", "").replace("-", "") + "USDT"
    if coin_id and coin_id in _sym_map:
        pair = _sym_map[coin_id] + "USDT"
    elif symbol_clean in _sym_map:
        pair = _sym_map[symbol_clean] + "USDT"

    # انتخاب interval بر اساس days
    if days <= 3:
        interval, limit = "15m", min(300, days * 96)
    elif days <= 14:
        interval, limit = "1h", min(400, days * 24)
    elif days <= 60:
        interval, limit = "4h", min(400, days * 6)
    else:
        interval, limit = "1d", min(400, days)

    klines = await _fetch_klines_interval(pair, interval, int(limit))
    if not klines or len(klines) < 20:
        return None, (
            f"❌ داده نموداری برای {pair} در دسترس نیست.\n"
            "مثال: btc ، eth ، sol ، ton"
        )

    try:
        import numpy as np
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle, FancyBboxPatch
        from matplotlib.collections import LineCollection
        plt.rcParams.update({
            "axes.unicode_minus": False,
            "font.family": "DejaVu Sans",
            "figure.facecolor": "#0b0e11",
            "axes.facecolor": "#0b0e11",
            "savefig.facecolor": "#0b0e11",
            "text.color": "#e5e7eb",
            "axes.labelcolor": "#9ca3af",
            "xtick.color": "#9ca3af",
            "ytick.color": "#9ca3af",
            "axes.edgecolor": "#1f2937",
            "grid.color": "#1f2937",
            "grid.linestyle": "-",
            "grid.linewidth": 0.6,
            "grid.alpha": 0.9,
        })
    except ImportError as e:
        return None, f"❌ کتابخانه رسم نصب نیست: {e}"

    opens = np.array([float(k[1]) for k in klines], dtype=float)
    highs = np.array([float(k[2]) for k in klines], dtype=float)
    lows = np.array([float(k[3]) for k in klines], dtype=float)
    closes = np.array([float(k[4]) for k in klines], dtype=float)
    vols = np.array([float(k[5]) for k in klines], dtype=float)
    n = len(closes)
    x = np.arange(n, dtype=float)

    def _ema(arr, period):
        out = np.zeros(len(arr), dtype=float)
        out[0] = arr[0]
        a = 2.0 / (period + 1)
        for i in range(1, len(arr)):
            out[i] = a * arr[i] + (1 - a) * out[i - 1]
        return out

    def _rsi_arr(c, period=14):
        out = np.full(len(c), np.nan)
        if len(c) <= period:
            return out
        diff = np.diff(c)
        gains = np.where(diff > 0, diff, 0.0)
        losses = np.where(diff < 0, -diff, 0.0)
        ag = gains[:period].mean()
        al = losses[:period].mean()
        out[period] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
        for i in range(period, len(diff)):
            ag = (ag * (period - 1) + gains[i]) / period
            al = (al * (period - 1) + losses[i]) / period
            out[i + 1] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
        return out

    def _adx_arr(h, l, c, period=14):
        out = np.full(len(c), np.nan)
        if len(c) < period + 2:
            return out
        tr = np.zeros(len(c))
        dp = np.zeros(len(c))
        dm = np.zeros(len(c))
        for i in range(1, len(c)):
            tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
            up = h[i] - h[i - 1]
            dn = l[i - 1] - l[i]
            dp[i] = up if up > dn and up > 0 else 0
            dm[i] = dn if dn > up and dn > 0 else 0
        atr = np.zeros(len(c))
        atr[period] = tr[1:period + 1].mean()
        for i in range(period + 1, len(c)):
            atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
        dxs = []
        for i in range(period, len(c)):
            atr_v = atr[i] if atr[i] > 0 else 1e-9
            di_p = 100 * (dp[i - period + 1:i + 1].mean()) / atr_v
            di_m = 100 * (dm[i - period + 1:i + 1].mean()) / atr_v
            s = di_p + di_m
            dx = 0 if s == 0 else 100 * abs(di_p - di_m) / s
            dxs.append(dx)
            out[i] = float(np.mean(dxs[-period:])) if len(dxs) >= period else dx
        return out

    ema20 = _ema(closes, 20)
    ema50 = _ema(closes, 50) if n >= 50 else _ema(closes, max(10, n // 3))
    ema100 = _ema(closes, 100) if n >= 100 else None
    bb_period = 20
    sma = np.array([closes[max(0, i - bb_period + 1):i + 1].mean() for i in range(n)])
    std = np.array([closes[max(0, i - bb_period + 1):i + 1].std() for i in range(n)])
    bb_u, bb_l = sma + 2 * std, sma - 2 * std
    rsi = _rsi_arr(closes, 14)
    adx = _adx_arr(highs, lows, closes, 14)

    # رنگ‌های حرفه‌ای
    C_UP = "#26a69a"
    C_DN = "#ef5350"
    C_EMA20 = "#42a5f5"
    C_EMA50 = "#ffa726"
    C_EMA100 = "#ab47bc"
    C_BB = "#5c6bc0"
    C_GRID = "#1e222d"
    C_TEXT = "#d1d4dc"
    C_MUTED = "#787b86"

    try:
        fig = plt.figure(figsize=(12, 9), dpi=140)
        gs = fig.add_gridspec(4, 1, height_ratios=[3.4, 0.85, 0.85, 0.85], hspace=0.06)
        ax_p = fig.add_subplot(gs[0])
        ax_v = fig.add_subplot(gs[1], sharex=ax_p)
        ax_a = fig.add_subplot(gs[2], sharex=ax_p)
        ax_r = fig.add_subplot(gs[3], sharex=ax_p)

        for ax in (ax_p, ax_v, ax_a, ax_r):
            ax.set_facecolor("#131722")
            ax.tick_params(colors=C_MUTED, labelsize=8)
            ax.grid(True, color=C_GRID, linewidth=0.7)
            for spine in ax.spines.values():
                spine.set_color("#2a2e39")

        # Bollinger fill
        ax_p.fill_between(x, bb_l, bb_u, color=C_BB, alpha=0.12, zorder=1)
        ax_p.plot(x, bb_u, color=C_BB, linewidth=0.7, alpha=0.5, linestyle="--", zorder=2)
        ax_p.plot(x, bb_l, color=C_BB, linewidth=0.7, alpha=0.5, linestyle="--", zorder=2)
        ax_p.plot(x, sma, color=C_BB, linewidth=0.9, alpha=0.7, zorder=2)

        # Candles — wick + body تمیز
        width = 0.62
        for i in range(n):
            up = closes[i] >= opens[i]
            color = C_UP if up else C_DN
            ax_p.plot([i, i], [lows[i], highs[i]], color=color, linewidth=1.0, solid_capstyle="round", zorder=3)
            body = abs(closes[i] - opens[i])
            bottom = min(opens[i], closes[i])
            if body < (highs[i] - lows[i]) * 0.002:
                body = max((highs[i] - lows[i]) * 0.015, closes[i] * 0.00008)
            ax_p.add_patch(Rectangle(
                (i - width / 2, bottom), width, body,
                facecolor=color, edgecolor=color, linewidth=0.4, zorder=4, alpha=0.95,
            ))

        ax_p.plot(x, ema20, color=C_EMA20, linewidth=1.35, label="EMA 20", zorder=5)
        ax_p.plot(x, ema50, color=C_EMA50, linewidth=1.35, label="EMA 50", zorder=5)
        if ema100 is not None:
            ax_p.plot(x, ema100, color=C_EMA100, linewidth=1.2, label="EMA 100", zorder=5)

        last = float(closes[-1])
        chg = ((closes[-1] - closes[0]) / closes[0] * 100) if closes[0] else 0
        chg_c = C_UP if chg >= 0 else C_DN
        ax_p.set_title(
            f"{pair}   •   {days}D ({interval})   •   ${last:,.2f}   ({chg:+.2f}%)",
            fontsize=13, fontweight="bold", color=C_TEXT, loc="left", pad=10,
        )
        leg = ax_p.legend(loc="upper left", fontsize=8, frameon=True, fancybox=True)
        leg.get_frame().set_facecolor("#1c2030")
        leg.get_frame().set_edgecolor("#2a2e39")
        for txt in leg.get_texts():
            txt.set_color(C_TEXT)
        ax_p.set_ylabel("Price (USDT)", fontsize=9, color=C_MUTED)
        # آخرین قیمت خط افقی
        ax_p.axhline(last, color=chg_c, linewidth=0.8, linestyle=":", alpha=0.7, zorder=2)
        ax_p.margins(x=0.01)
        plt.setp(ax_p.get_xticklabels(), visible=False)

        # Volume
        vcolors = [C_UP if closes[i] >= opens[i] else C_DN for i in range(n)]
        ax_v.bar(x, vols, color=vcolors, width=0.7, alpha=0.85, zorder=3)
        ax_v.set_ylabel("Volume", fontsize=8, color=C_MUTED)
        plt.setp(ax_v.get_xticklabels(), visible=False)
        ax_v.margins(x=0.01)

        # ADX
        ax_a.plot(x, adx, color="#b2b5be", linewidth=1.25, label="ADX(14)", zorder=3)
        ax_a.axhline(25, color="#787b86", linestyle="--", linewidth=0.8, alpha=0.8)
        ax_a.fill_between(x, adx, 25, where=(~np.isnan(adx)) & (adx >= 25), color="#26a69a", alpha=0.15)
        ax_a.set_ylabel("ADX", fontsize=8, color=C_MUTED)
        ax_a.set_ylim(0, max(60, np.nanmax(adx) * 1.15 if np.nanmax(adx) == np.nanmax(adx) else 60))
        la = ax_a.legend(loc="upper left", fontsize=7, frameon=True)
        la.get_frame().set_facecolor("#1c2030")
        la.get_frame().set_edgecolor("#2a2e39")
        for txt in la.get_texts():
            txt.set_color(C_TEXT)
        plt.setp(ax_a.get_xticklabels(), visible=False)
        ax_a.margins(x=0.01)

        # RSI
        ax_r.plot(x, rsi, color="#e0e3eb", linewidth=1.25, label="RSI(14)", zorder=3)
        ax_r.axhline(70, color=C_DN, linestyle="--", linewidth=0.8, alpha=0.7)
        ax_r.axhline(30, color=C_UP, linestyle="--", linewidth=0.8, alpha=0.7)
        ax_r.axhline(50, color="#787b86", linestyle=":", linewidth=0.6, alpha=0.5)
        ax_r.fill_between(x, 70, 100, color=C_DN, alpha=0.06)
        ax_r.fill_between(x, 0, 30, color=C_UP, alpha=0.06)
        ax_r.set_ylim(0, 100)
        ax_r.set_ylabel("RSI", fontsize=8, color=C_MUTED)
        lr = ax_r.legend(loc="upper left", fontsize=7, frameon=True)
        lr.get_frame().set_facecolor("#1c2030")
        lr.get_frame().set_edgecolor("#2a2e39")
        for txt in lr.get_texts():
            txt.set_color(C_TEXT)
        ax_r.margins(x=0.01)

        # X labels
        step = max(1, n // 7)
        ticks = list(range(0, n, step))
        if n - 1 not in ticks:
            ticks.append(n - 1)
        labels = []
        for i in ticks:
            ts = int(klines[i][0])
            if ts < 1e12:
                ts *= 1000
            dt = datetime.utcfromtimestamp(ts / 1000.0)
            labels.append(dt.strftime("%m/%d" if days > 5 else "%m/%d %H:%M"))
        ax_r.set_xticks(ticks)
        ax_r.set_xticklabels(labels, rotation=0, fontsize=8, color=C_MUTED)

        fig.subplots_adjust(left=0.07, right=0.98, top=0.93, bottom=0.06)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=140, facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close(fig)
        buf.seek(0)
        png = buf.read()
    except Exception as e:
        logger.error(f"chart draw: {e}")
        try:
            plt.close("all")
        except Exception:
            pass
        return None, f"❌ خطا در رسم نمودار: {e}"

    first, last = float(closes[0]), float(closes[-1])
    chg = ((last - first) / first * 100) if first else 0
    emoji = "🟢" if chg >= 0 else "🔴"
    caption = (
        f"📊 {pair} | {days}D ({interval})\n"
        f"${first:,.2f} → ${last:,.2f}  {emoji} {chg:+.2f}%\n"
        f"H/L: ${float(highs.max()):,.2f} / ${float(lows.min()):,.2f}"
    )
    return png, caption

async def _fetch_klines_interval(pair: str, interval: str, limit: int) -> list:
    key = f"klines:{pair}:{interval}:{limit}"
    now = asyncio.get_running_loop().time()
    cached = _HTTP_DATA_CACHE.get(key)
    if cached is not None and now - _HTTP_DATA_CACHE_T.get(key, 0) < MARKET_CACHE_TTLS["klines"]:
        return cached
    retries = max(0, int(__import__('os').getenv("MARKET_HTTP_RETRIES", "0")))
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        async with pooled_async_client() as c:
            r = await request_with_retry("GET", 
                "https://data-api.binance.vision/api/v3/klines", retries=retries,
                params={"symbol": pair, "interval": interval, "limit": limit},
            )
            if r.status_code == 200:
                data = safe_json(r) or []
                if data:
                    _HTTP_DATA_CACHE[key] = data
                    _HTTP_DATA_CACHE_T[key] = now
                    _trim_http_data_cache()
                    return data
            # OKX map
            okx_bar = {"15m": "15m", "1h": "1H", "4h": "4H", "1d": "1D"}.get(interval, "1H")
            okx_sym = pair.replace("USDT", "-USDT")
            r2 = await request_with_retry("GET", 
                "https://www.okx.com/api/v5/market/candles", retries=retries,
                params={"instId": okx_sym, "bar": okx_bar, "limit": str(min(limit, 300))},
            )
            if r2.status_code == 200:
                rows = (safe_json(r2) or {}).get("data") or []
                out = []
                for row in reversed(rows):
                    out.append([int(row[0]), row[1], row[2], row[3], row[4], row[5]])
                _HTTP_DATA_CACHE[key] = out
                _HTTP_DATA_CACHE_T[key] = now
                _trim_http_data_cache()
                return out
    except Exception as e:
        logger.warning(f"klines interval: {e}")
    return []

def _trim_http_data_cache() -> None:
    if len(_HTTP_DATA_CACHE) <= _HTTP_DATA_CACHE_MAX:
        return
    now = asyncio.get_running_loop().time()
    for key, ts in list(_HTTP_DATA_CACHE_T.items()):
        if now - ts >= _HTTP_DATA_CACHE_TTL:
            _HTTP_DATA_CACHE.pop(key, None)
            _HTTP_DATA_CACHE_T.pop(key, None)
    while len(_HTTP_DATA_CACHE) > _HTTP_DATA_CACHE_MAX:
        key = next(iter(_HTTP_DATA_CACHE))
        _HTTP_DATA_CACHE.pop(key, None)
        _HTTP_DATA_CACHE_T.pop(key, None)
