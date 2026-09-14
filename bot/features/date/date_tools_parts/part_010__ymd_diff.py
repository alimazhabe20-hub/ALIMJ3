# Auto-split part 10: _ymd_diff
def _ymd_diff(a, b):
    """اختلاف سال/ماه/روز بین دو jdatetime.date (a <= b)"""
    years = b.year - a.year
    months = b.month - a.month
    days = b.day - a.day
    if days < 0:
        months -= 1
        pm = b.month - 1 if b.month > 1 else 12
        py = b.year if b.month > 1 else b.year - 1
        days += _days_in_jmonth(py, pm)
    if months < 0:
        years -= 1
        months += 12
    return years, months, days
