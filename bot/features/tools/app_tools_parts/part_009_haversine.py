# Auto-split part 9: haversine
def haversine(lat1, lon1, lat2, lon2):
    """فاصله خط مستقیم روی کره زمین (کیلومتر) — دقیق"""
    R = 6371.0088  # میانگین شعاع زمین
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1 - a)))
