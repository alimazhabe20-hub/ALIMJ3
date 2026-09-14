# Auto-split part 13: enhance_ocr_prompt
def enhance_ocr_prompt(user_prompt: str, has_image: bool) -> str:
    if not has_image:
        return user_prompt
    base = (user_prompt or "").strip()
    if re.search(r"فیش|رسید|فاکتور|OCR|او\s*سی\s*آر|کارت\s*ملی|کارت\s*بانک", base, re.I):
        return RECEIPT_OCR_PROMPT + ("\n\nدرخواست کاربر: " + base if base else "")
    if not base:
        return (
            "تصویر را کامل تحلیل کن. اگر فیش/رسید/متن دارد، متن را دقیق بخوان و "
            "مبالغ و تاریخ را جداگانه لیست کن."
        )
    return base
