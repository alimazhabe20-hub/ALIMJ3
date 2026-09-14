# Auto-split part 12: _volume_breakout
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
