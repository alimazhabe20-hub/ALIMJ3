from typing import Optional

# Auto-split part 2: parse_natural_crypto_price
def parse_natural_crypto_price(text: str) -> Optional[str]:
    """تشخیص درخواست قیمت زنده یک رمزارز مشخص برای جلوگیری از پاسخ حدسی AI."""
    normalized = (text or "").strip().replace("ي", "ی").replace("ك", "ک").replace("‌", " ")
    if not re.search(r"قیمت|نرخ|چنده|چقدر|price", normalized, re.I):
        return None
    aliases = [
        (r"بیت\s*کوین|بیتکویین|bitcoin|btc", "btc"),
        (r"اتریوم|ethereum|eth", "eth"),
        (r"تتر|tether|usdt", "usdt"),
        (r"سولانا|solana|sol", "sol"),
        (r"ریپل|xrp", "xrp"),
        (r"دوج\s*کوین|dogecoin|doge", "doge"),
        (r"bnb|بایننس", "bnb"),
        (r"کاردانو|cardano|ada", "ada"),
    ]
    for pattern, symbol in aliases:
        if re.search(pattern, normalized, re.I):
            return symbol
    return None
