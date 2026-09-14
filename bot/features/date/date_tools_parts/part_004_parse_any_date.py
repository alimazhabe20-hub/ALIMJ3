# Auto-split part 4: parse_any_date
def parse_any_date(text: str):
    n = _norm(text.strip())
    m = re.match(r"^(\d{3,4})\s*/\s*(\d{1,2})\s*/\s*(\d{1,2})$", n)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1200 <= y <= 1500:
            return ("shamsi", y, mo, d)
        if 1800 <= y <= 2100:
            return ("gregorian", y, mo, d)
        if 1300 <= y <= 1600:
            return ("hijri", y, mo, d)
    for name, num in PERSIAN_MONTHS_REV.items():
        if name in text:
            nums = re.findall(r"\d+", n)
            if len(nums) >= 2:
                return ("shamsi", int(nums[-1]), num, int(nums[0]))
    for name, num in HIJRI_MONTHS_REV.items():
        if name in text:
            nums = re.findall(r"\d+", n)
            if len(nums) >= 2:
                return ("hijri", int(nums[-1]), num, int(nums[0]))
    return None
