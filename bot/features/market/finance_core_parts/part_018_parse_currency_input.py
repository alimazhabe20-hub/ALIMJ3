# Auto-split part 18: parse_currency_input
def parse_currency_input(text: str) -> tuple[float, str, str] | None:
    """پارس هوشمند: عدد + ارز مبدا + ارز مقصد (فارسی/انگلیسی)"""
    if not text:
        return None
    t = text.strip().translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
    t = t.replace("،", "").replace(",", "")
    t_lower = t.lower().replace("‌", " ").replace("  ", " ").strip()

    # الگوهای رایج
    # 1) 20 ton / 1.5 btc usdt / 100 دلار تومان
    m = re.match(
        r"^([\d.]+)\s*([a-zA-Zآ-ی]+)?\s*(?:به|to|=|→|->)?\s*([a-zA-Zآ-ی]+)?\s*$",
        t_lower,
    )
    if m:
        amount = float(m.group(1))
        a = (m.group(2) or "").strip()
        b = (m.group(3) or "").strip()
        # نرمال‌سازی فارسی
        a = _FA_CURRENCY.get(a, a)
        b = _FA_CURRENCY.get(b, b)
        return amount, a, b

    # 2) فقط عدد و یک کلمه چسبیده: 100دلار
    m2 = re.match(r"^([\d.]+)\s*([a-zA-Zآ-ی]+)\s*$", t_lower)
    if m2:
        amount = float(m2.group(1))
        a = _FA_CURRENCY.get(m2.group(2).strip(), m2.group(2).strip())
        return amount, a, ""

    return None
