# Auto-split part 9: _days_in_jmonth
def _days_in_jmonth(year, month):
    """تعداد روز ماه شمسی (درست برای کبیسه)"""
    days = jdatetime.j_days_in_month[month - 1]
    if month == 12 and jdatetime.date(year, 1, 1).isleap():
        days = 30
    return days
