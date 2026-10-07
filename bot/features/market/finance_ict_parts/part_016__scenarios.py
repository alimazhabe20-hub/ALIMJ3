# Auto-split part 16: _scenarios
def _scenarios(bias: dict, dr: dict, liq: dict, ext: dict) -> list[str]:
    notes = []
    side = bias.get("side")
    if side == "bullish":
        notes.append(
            "سناریو صعودی: حفظ ساختار HH/HL، برگشت از Discount/OTE یا FVG صعودی، "
            "با هدف نقدینگی بالای BSL."
        )
        if liq.get("bsl"):
            notes.append(f"هدف نقدینگی بالقوه (BSL): {liq['bsl']:.6g}")
        if ext.get("last_low"):
            notes.append(f"نقض سناریو: کلوز پایدار زیر {ext['last_low']:.6g}")
    elif side == "bearish":
        notes.append(
            "سناریو نزولی: حفظ LH/LL، برگشت از Premium/OTE یا FVG نزولی، "
            "با هدف نقدینگی زیر SSL."
        )
        if liq.get("ssl"):
            notes.append(f"هدف نقدینگی بالقوه (SSL): {liq['ssl']:.6g}")
        if ext.get("last_high"):
            notes.append(f"نقض سناریو: کلوز پایدار بالای {ext['last_high']:.6g}")
    else:
        notes.append(
            "سناریو خنثی: تا BOS/MSS واضح یا ورود قیمت به OTE همراه با Displacement، "
            "از ورود عجولانه خودداری کنید."
        )
    return notes
