# Auto-split part 2: _norm_digits
def _norm_digits(s: str) -> str:
    return str(s).translate(
        str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    )
