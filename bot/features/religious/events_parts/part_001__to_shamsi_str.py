# Auto-split part 1: _to_shamsi_str
def _to_shamsi_str(gregorian_date) -> str:
    try:
        if jdatetime is not None:
            jd = jdatetime.date.fromgregorian(date=gregorian_date)
            return f"{jd.year}/{jd.month:02d}/{jd.day:02d}"
        # Dependency-free Gregorian -> Jalali fallback.
        gy, gm, gd = gregorian_date.year, gregorian_date.month, gregorian_date.day
        gdm = [0,31,59,90,120,151,181,212,243,273,304,334]
        gy2 = gy + 1 if gm > 2 else gy
        days = 355666 + 365*gy + (gy2+3)//4 - (gy2+99)//100 + (gy2+399)//400 + gd + gdm[gm-1]
        jy = -1595 + 33*(days//12053)
        days %= 12053
        jy += 4*(days//1461); days %= 1461
        if days > 365:
            jy += (days-1)//365; days = (days-1)%365
        if days < 186:
            jm = 1 + days//31; jd = 1 + days%31
        else:
            jm = 7 + (days-186)//30; jd = 1 + (days-186)%30
        return f"{jy}/{jm:02d}/{jd:02d}"
    except Exception:
        return str(gregorian_date)
