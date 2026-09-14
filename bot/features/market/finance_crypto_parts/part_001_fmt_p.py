# Auto-split part 1: fmt_p
def fmt_p(v):
    if v is None:
        return "—"
    try:
        v = float(v)
    except Exception:
        return "—"
    return f"{v:,.2f}" if abs(v) >= 1 else f"{v:,.4f}"
