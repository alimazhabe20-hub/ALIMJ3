# Auto-split part 2: _normalize
def _normalize(text: str) -> str:
    """تبدیل اعداد فارسی/عربی به انگلیسی و یکدست‌سازی جداکننده‌ها"""
    fa = "۰۱۲۳۴۵۶۷۸۹"
    ar = "٠١٢٣٤٥٦٧٨٩"
    en = "0123456789"
    table = str.maketrans(fa + ar, en + en)
    text = text.translate(table)
    text = text.replace("ـ", "-").replace("٫", ".").replace("،", ",")
    text = re.sub(r"[\/\-\.]", "/", text)
    return text.strip()
