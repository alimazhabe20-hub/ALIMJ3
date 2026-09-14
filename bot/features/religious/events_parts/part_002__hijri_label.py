# Auto-split part 2: _hijri_label
def _hijri_label(hijri) -> str:
    month_name = HIJRI_MONTH_NAMES.get(hijri.month, str(hijri.month))
    return f"{hijri.day} {month_name} {hijri.year}"
