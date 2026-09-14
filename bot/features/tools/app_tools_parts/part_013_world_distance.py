# Auto-split part 13: world_distance
async def world_distance(place1: str, place2: str = None) -> str:
    if place2 is None:
        parsed = parse_two_places(place1)
        if not parsed:
            return (
                "❌ دو مکان بنویسید.\n\n"
                "مثال‌ها:\n"
                "• تهران تا مشهد\n"
                "• قم کربلا\n"
                "• تهران تا ترکیه\n"
                "• Paris to Tokyo\n"
                "• New York to London"
            )
        place1, place2 = parsed

    place1, place2 = place1.strip(), place2.strip()
    g1, g2 = await asyncio.gather(geocode(place1), geocode(place2))
    if not g1:
        return f"❌ «{place1}» پیدا نشد.\nنام شهر یا کشور را دقیق‌تر بنویسید."
    if not g2:
        return f"❌ «{place2}» پیدا نشد.\nنام شهر یا کشور را دقیق‌تر بنویسید."

    lat1, lon1, n1 = g1
    lat2, lon2, n2 = g2
    km = haversine(lat1, lon1, lat2, lon2)
    miles = km * 0.621371

    if km < 0.05:
        return (
            f"🗺 فاصله جهانی\n\n"
            f"از: {n1}\nتا: {n2}\n\n"
            f"📏 این دو نقطه تقریباً یکی هستند (کمتر از ۵۰ متر)."
        )

    # فاصله جاده‌ای (اختیاری)
    driving_info = ""
    try:
        from bot.config import config
        gkey = getattr(config, "GOOGLE_MAPS_API_KEY", "") or ""
        if gkey:
            async with httpx.AsyncClient(timeout=12.0) as client:
                r = await client.get(
                    "https://maps.googleapis.com/maps/api/distancematrix/json",
                    params={
                        "origins": f"{lat1},{lon1}",
                        "destinations": f"{lat2},{lon2}",
                        "mode": "driving",
                        "language": "fa",
                        "units": "metric",
                        "key": gkey,
                    },
                )
                if r.status_code == 200:
                    el = ((r.json().get("rows") or [{}])[0].get("elements") or [{}])[0]
                    if el.get("status") == "OK":
                        dist_txt = (el.get("distance") or {}).get("text", "")
                        dur_txt = (el.get("duration") or {}).get("text", "")
                        if dist_txt:
                            driving_info = f"🚗 جاده (گوگل): {dist_txt} — حدود {dur_txt}\n"
        if not driving_info and km < 3000:
            osrm = await _osrm_driving(lat1, lon1, lat2, lon2)
            if osrm:
                d_km, d_hr = osrm
                driving_info = (
                    f"🚗 جاده (تقریبی OSRM): {pn(f'{d_km:,.0f}')} کیلومتر — "
                    f"حدود {_fmt_duration(d_hr)}\n"
                )
    except Exception as e:
        logger.warning(f"driving: {e}")

    return (
        f"🗺 فاصله جهانی\n\n"
        f"📍 از: {n1}\n"
        f"📍 تا: {n2}\n\n"
        f"📏 خط مستقیم (هوایی):\n"
        f"   {pn(f'{km:,.1f}')} کیلومتر\n"
        f"   {pn(f'{miles:,.1f}')} مایل\n\n"
        f"{driving_info}"
        f"⏱ زمان تقریبی با خط مستقیم:\n"
        f"🚗 خودرو (~۸۰km/h): {_fmt_duration(km / 80)}\n"
        f"✈️ هواپیما: {_fmt_duration(km / 800 + 0.5)}\n"
        f"🚶 پیاده: {_fmt_duration(km / 5)}\n\n"
        f"📌 مختصات:\n"
        f"{n1}: {lat1:.4f}, {lon1:.4f}\n"
        f"{n2}: {lat2:.4f}, {lon2:.4f}"
    )
