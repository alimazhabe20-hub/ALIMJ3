# Auto-split part 2: _norm
def _norm(text: str) -> str:
    fa, ar, en = "۰۱۲۳۴۵۶۷۸۹", "٠١٢٣٤٥٦٧٨٩", "0123456789"
    text = text.translate(str.maketrans(fa + ar, en + en))
    text = text.replace("ـ", "-").replace("٫", ".")
    return re.sub(r"[\/\-\.]", "/", text.strip())
