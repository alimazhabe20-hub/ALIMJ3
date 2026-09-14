# Auto-split part 6: city_distance
def city_distance(city1: str, city2: str) -> str:
    """فاصله دقیق بین دو شهر با فرمول Haversine"""
    c1 = CITY_COORDS.get(city1.strip())
    c2 = CITY_COORDS.get(city2.strip())
    if not c1 or not c2:
        available = "، ".join(list(CITY_COORDS.keys())[:15]) + " و ..."
        return (
            f"❌ یکی از شهرها پیدا نشد.\n\n"
            f"شهرهای پشتیبانی‌شده:\n{available}\n\n"
            f"مثال: `تهران مشهد`"
        )
    R = 6371.0
    lat1, lon1 = math.radians(c1[0]), math.radians(c1[1])
    lat2, lon2 = math.radians(c2[0]), math.radians(c2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    dist = 2 * R * math.asin(math.sqrt(a))
    hours = dist / 80
    h = int(hours)
    m = int((hours - h) * 60)
    return (
        f"🗺 **فاصله بین شهرها**\n\n"
        f"📍 {city1}  ↔  {city2}\n\n"
        f"📏 فاصله هوایی: **{pn(f'{dist:.0f}')} کیلومتر**\n"
        f"🚗 تقریبی با خودرو: حدود **{pn(h)} ساعت و {pn(m)} دقیقه**"
    )
