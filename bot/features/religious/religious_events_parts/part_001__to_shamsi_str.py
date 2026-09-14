# Auto-split part 1: _to_shamsi_str
def _to_shamsi_str(gregorian_date) -> str:
    try:
        jd = jdatetime.date.fromgregorian(date=gregorian_date)
        return f"{jd.year}/{jd.month:02d}/{jd.day:02d}"
    except Exception:
        return str(gregorian_date)
