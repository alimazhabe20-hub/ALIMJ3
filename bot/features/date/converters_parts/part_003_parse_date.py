# Auto-split part 3: parse_date
def parse_date(text: str):
    """
    تشخیص و پارس تاریخ از متن کاربر.
    خروجی: (نوع, year, month, day)  یا None
    نوع: 'shamsi' | 'gregorian' | 'hijri'
    """
    text = text.strip()
    if not text:
        return None

    normalized = _normalize(text)

    # الگوی عددی: 1403/5/18 یا 2024/08/09
    m = re.match(r"^(\d{3,4})\s*/\s*(\d{1,2})\s*/\s*(\d{1,2})$", normalized)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1200 <= y <= 1500:
            return ("shamsi", y, mo, d)
        if 1800 <= y <= 2100:
            return ("gregorian", y, mo, d)
        if 1300 <= y <= 1600:  # قمری نزدیک به شمسی
            # اگر ماه > ۱۲ نیست و سال در محدوده قمری است
            return ("hijri", y, mo, d)
        return None

    # الگوی با نام ماه شمسی: 18 مرداد 1403
    for name, num in PERSIAN_MONTHS_REV.items():
        if name in text:
            nums = re.findall(r"\d+", _normalize(text))
            if len(nums) >= 2:
                # معمولاً روز و سال
                day = int(nums[0])
                year = int(nums[-1])
                if 1200 <= year <= 1500 and 1 <= day <= 31:
                    return ("shamsi", year, num, day)
            break

    # الگوی با نام ماه قمری: 15 صفر 1446
    for name, num in HIJRI_MONTHS_REV.items():
        if name in text:
            nums = re.findall(r"\d+", _normalize(text))
            if len(nums) >= 2:
                day = int(nums[0])
                year = int(nums[-1])
                if 1300 <= year <= 1600 and 1 <= day <= 30:
                    return ("hijri", year, num, day)
            break

    return None
