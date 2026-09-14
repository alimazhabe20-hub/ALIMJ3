# Auto-split part 15: parse_two_dates
def parse_two_dates(text: str):
    """پارس دو تاریخ شمسی از یک متن"""
    normalized = _normalize(text)
    matches = re.findall(r"(\d{3,4})\s*/\s*(\d{1,2})\s*/\s*(\d{1,2})", normalized)
    if len(matches) >= 2:
        a = tuple(int(x) for x in matches[0])
        b = tuple(int(x) for x in matches[1])
        if 1200 <= a[0] <= 1500 and 1200 <= b[0] <= 1500:
            return a, b
    return None
