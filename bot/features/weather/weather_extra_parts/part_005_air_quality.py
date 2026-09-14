# Auto-split part 5: air_quality
async def air_quality(city: str) -> str:
    """شاخص کیفیت هوا واقعی با Open-Meteo Air Quality API"""
    key = f"aqi_{city}"
    now = datetime.now().timestamp()
    if key in _cache and now - _cache_t.get(key, 0) < config.CACHE_TTL:
        return _cache[key]

    lat, lon = _get_coords(city)
    try:
        url = "https://air-quality-api.open-meteo.com/v1/air-quality"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "european_aqi,pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,ozone,sulphur_dioxide,dust",
            "timezone": "Asia/Tehran",
        }
        async with pooled_async_client() as client:
            r = await request_with_retry("GET", url, params=params)
            r.raise_for_status()
            data = r.json()

        cur = data.get("current", {})
        aqi = cur.get("european_aqi")
        pm25 = cur.get("pm2_5")
        pm10 = cur.get("pm10")
        no2 = cur.get("nitrogen_dioxide")
        o3 = cur.get("ozone")
        so2 = cur.get("sulphur_dioxide")
        co = cur.get("carbon_monoxide")
        dust = cur.get("dust")

        label, advice = "نامشخص", ""
        if aqi is not None:
            for low, high, lab, adv in AQI_LABELS:
                if low <= aqi <= high:
                    label, advice = lab, adv
                    break

        lines = [
            f"🌫 **کیفیت هوا — {city}** (زمان واقعی)\n",
            f"📊 **شاخص AQI (اروپایی):** {pn(aqi) if aqi is not None else '—'}  →  **{label}**\n",
            f"💡 {advice}\n" if advice else "",
            "━━━━━━━━━━━━━━━━━━━━",
            f"• PM2.5: {pn(pm25) if pm25 is not None else '—'} µg/m³",
            f"• PM10: {pn(pm10) if pm10 is not None else '—'} µg/m³",
            f"• NO₂: {pn(no2) if no2 is not None else '—'} µg/m³",
            f"• O₃: {pn(o3) if o3 is not None else '—'} µg/m³",
            f"• SO₂: {pn(so2) if so2 is not None else '—'} µg/m³",
            f"• CO: {pn(co) if co is not None else '—'} µg/m³",
        ]
        if dust is not None:
            lines.append(f"• گردوغبار: {pn(dust)} µg/m³")

        result = "\n".join(lines)
        _cache[key] = result
        _cache_t[key] = now
        return result
    except Exception as e:
        logger.error(f"aqi {city}: {e}")
        return f"❌ کیفیت هوای {city} موقتاً در دسترس نیست."
