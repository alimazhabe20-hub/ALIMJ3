# Auto-split part 1: to_persian_num
def to_persian_num(num):
    mapping = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    return str(num).translate(mapping)
