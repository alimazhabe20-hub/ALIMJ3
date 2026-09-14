from typing import List
from typing import Optional
from typing import Tuple

# Auto-split part 10: parse_chart_request
def parse_chart_request(text: str) -> Optional[Tuple[str, List[str], List[float], str]]:
    """
    تلاش برای فهم درخواست نمودار از متن.
    مثال: نمودار میله‌ای قیمت: دلار 60000، یورو 65000
    """
    t = (text or "").strip()
    if not re.search(r"نمودار|chart|گراف", t, re.I):
        return None
    ctype = "bar"
    if re.search(r"خطی|line", t, re.I):
        ctype = "line"
    elif re.search(r"دایره|pie", t, re.I):
        ctype = "pie"

    # pairs: name number
    pairs = re.findall(
        r"([A-Za-zآ-یء‌]+)\s*[:=：]?\s*([0-9۰-۹]+(?:[.,][0-9۰-۹]+)?)",
        t,
    )
    if len(pairs) < 2:
        return None

    def _num(s: str) -> float:
        s = s.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")).replace(",", "")
        return float(s)

    labels = [p[0] for p in pairs]
    values = [_num(p[1]) for p in pairs]
    title = "نمودار"
    m = re.search(r"نمودار\s*([^:\n]+)", t)
    if m:
        title = m.group(1).strip()[:60] or title
    return title, labels, values, ctype
