from typing import Any

# Auto-split part 3: _price
def _price(value: Any) -> int | None:
    if value is None:
        return None
    s = _norm_digits(str(value)).replace("٬", "").replace(",", "").replace(" ", "")
    m = re.search(r"\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        n = float(m.group())
    except Exception:
        return None
    return int(n)
