# Auto-split part 8: get_gold_chart
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
