from typing import Any

# Auto-split part 4: _currency_and_price
def _currency_and_price(raw: Any, currency: str = "") -> tuple[int | None, str]:
    p = _price(raw)
    cur = (currency or "").lower()
    if p is not None and ("rial" in cur or "ریال" in cur):
        p = p // 10
        return p, "تومان"
    if p is not None:
        return p, "تومان"
    return None, "تومان"
