from typing import Any

# Auto-split part 2: pn
def pn(n: Any) -> str:
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
