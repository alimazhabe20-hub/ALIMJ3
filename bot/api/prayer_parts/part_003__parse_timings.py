# Auto-split part 3: _parse_timings
def _parse_timings(timings: dict) -> dict:
    """تبدیل کلیدهای انگلیسی به فارسی"""
    return {
        "اذان صبح": timings["Fajr"],
        "طلوع آفتاب": timings["Sunrise"],
        "اذان ظهر": timings["Dhuhr"],
        "اذان عصر": timings["Asr"],
        "اذان مغرب": timings["Maghrib"],
        "اذان عشاء": timings["Isha"],
    }
