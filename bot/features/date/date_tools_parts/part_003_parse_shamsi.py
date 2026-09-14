# Auto-split part 3: parse_shamsi
def parse_shamsi(text: str):
    text = text.strip()
    n = _norm(text)
    m = re.match(r"^(\d{3,4})\s*/\s*(\d{1,2})\s*/\s*(\d{1,2})(?:\s+(\d{1,2}):(\d{1,2}))?$", n)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        h = int(m.group(4)) if m.group(4) else 0
        mi = int(m.group(5)) if m.group(5) else 0
        if 1200 <= y <= 1500:
            return (y, mo, d, h, mi)
    for name, num in PERSIAN_MONTHS_REV.items():
        if name in text:
            nums = re.findall(r"\d+", n)
            if len(nums) >= 2:
                day, year = int(nums[0]), int(nums[-1])
                if 1200 <= year <= 1500:
                    return (year, num, day, 0, 0)
            break
    return None
