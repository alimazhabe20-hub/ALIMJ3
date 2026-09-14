# Auto-split part 2: _normalize
def _normalize(text: str) -> str:
    text = (text or "").lower()
    replacements = {
        "ي": "ی", "ى": "ی", "ك": "ک", "ۀ": "ه", "ة": "ه",
        "ؤ": "و", "إ": "ا", "أ": "ا", "ٱ": "ا",
        "۰": "0", "۱": "1", "۲": "2", "۳": "3", "۴": "4",
        "۵": "5", "۶": "6", "۷": "7", "۸": "8", "۹": "9",
    }
    for a, b in replacements.items():
        text = text.replace(a, b)
    text = re.sub(r"[^\w\u0600-\u06ff\s.-]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()
