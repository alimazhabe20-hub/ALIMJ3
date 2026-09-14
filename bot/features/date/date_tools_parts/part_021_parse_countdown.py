# Auto-split part 21: parse_countdown
def parse_countdown(text: str):
    p = parse_shamsi(text)
    if not p:
        # تاریخ + برچسب
        n = _norm(text)
        m = re.search(r"(\d{3,4})\s*/\s*(\d{1,2})\s*/\s*(\d{1,2})", n)
        if m:
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            label = re.sub(r"\d{3,4}\s*[/\-\.]\s*\d{1,2}\s*[/\-\.]\s*\d{1,2}", "", text).strip() or "رویداد"
            return (y, mo, d, label)
        return None
    y, m, d, _, _ = p
    label = re.sub(r"\d{3,4}\s*[/\-\.]\s*\d{1,2}\s*[/\-\.]\s*\d{1,2}", "", text).strip() or "رویداد"
    return (y, m, d, label)
