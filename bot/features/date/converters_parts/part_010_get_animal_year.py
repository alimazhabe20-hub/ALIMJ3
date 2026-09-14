# Auto-split part 10: get_animal_year
def get_animal_year(shamsi_year: int) -> str:
    """حیوان سال بر اساس سال شمسی (چرخه ۱۲ ساله)"""
    # سال ۱۳۰۹ = اسب (شاخص رایج)
    idx = (shamsi_year - 1309) % 12
    return CHINESE_ANIMALS[idx]
