# Auto-split part 10: _fmt_duration
def _fmt_duration(hours: float) -> str:
    if hours is None or hours < 0:
        return "—"
    if hours < 0.02:
        return "کمتر از ۱ دقیقه"
    if hours < 1:
        return f"{pn(int(hours * 60))} دقیقه"
    h = int(hours)
    m = int((hours - h) * 60)
    if h >= 24:
        d, h2 = h // 24, h % 24
        return f"{pn(d)} روز و {pn(h2)} ساعت" if h2 else f"{pn(d)} روز"
    return f"{pn(h)} ساعت و {pn(m)} دقیقه" if m else f"{pn(h)} ساعت"
