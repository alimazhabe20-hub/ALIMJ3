# Auto-split part 12: _osrm_driving
async def _osrm_driving(lat1, lon1, lat2, lon2):
    """فاصله جاده‌ای رایگان با OSRM — ممکن است برای بعضی مسیرها None باشد"""
    try:
        url = f"https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}"
        async with httpx.AsyncClient(timeout=12.0) as client:
            r = await client.get(url, params={"overview": "false"})
            if r.status_code != 200:
                return None
            js = r.json() or {}
            if js.get("code") != "Ok":
                return None
            routes = js.get("routes") or []
            if not routes:
                return None
            meters = float(routes[0].get("distance") or 0)
            seconds = float(routes[0].get("duration") or 0)
            return meters / 1000.0, seconds / 3600.0
    except Exception as e:
        logger.warning(f"osrm: {e}")
        return None
