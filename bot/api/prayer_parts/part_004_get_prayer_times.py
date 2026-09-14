# Auto-split part 4: get_prayer_times
def get_prayer_times(city, country="Iran", method=None):
    """
    دریافت اوقات شرعی با اولویت مختصات دقیق.
    اگر مختصات شهر موجود باشد از /timings استفاده می‌کند (دقت بالا)،
    در غیر این صورت به timingsByCity برمی‌گردد.
    """
    method = method if method is not None else config.PRAYER_METHOD
    city = city or "قم"
    key = f"{city}_{country}_{method}"
    now = datetime.now().timestamp()

    if key in _cache_data and now - _cache_time.get(key, 0) < config.CACHE_TTL:
        return _cache_data[key]

    try:
        coords = _get_coords(city)
        if coords:
            lat, lon = coords
            url = (
                f"https://api.aladhan.com/v1/timings"
                f"?latitude={lat}&longitude={lon}"
                f"&method={method}&school=0"
            )
            logger.debug(f"Prayer times via coords for {city}: {lat}, {lon}")
        else:
            # fallback به نام شهر
            url = (
                f"https://api.aladhan.com/v1/timingsByCity"
                f"?city={city}&country={country}"
                f"&method={method}&school=0"
            )
            logger.debug(f"Prayer times via city name for {city}")

        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        timings = data["data"]["timings"]
        result = _parse_timings(timings)

        _cache_data[key] = result
        _cache_time[key] = now
        return result

    except Exception as e:
        logger.error(f"Error fetching prayer times for {city}: {e}")
        return None
