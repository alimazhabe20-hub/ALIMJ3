# Auto-split part 1: pn
def pn(num):
    return str(num).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
