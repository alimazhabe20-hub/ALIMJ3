# Auto-split part 6: get_prayer_times_for_date
def get_prayer_times_for_date(city, date_str, country="Iran", method=None):
    """
    اوقات شرعی برای یک تاریخ مشخص
    date_str باید به فرمت DD-MM-YYYY باشد
    """
    method = method if method is not None else config.PRAYER_METHOD
    city = city or "قم"
    key = f"{city}_{country}_{date_str}_{method}"
    now = datetime.now().timestamp()

    if key in _cache_data and now - _cache_time.get(key, 0) < config.CACHE_TTL:
        return _cache_data[key]

    try:
        coords = _get_coords(city)
        if coords:
            lat, lon = coords
            url = (
                f"https://api.aladhan.com/v1/timings/{date_str}"
                f"?latitude={lat}&longitude={lon}"
                f"&method={method}&school=0"
            )
        else:
            url = (
                f"https://api.aladhan.com/v1/timingsByCity/{date_str}"
                f"?city={city}&country={country}"
                f"&method={method}&school=0"
            )

        response = requests.get(url, timeout=10)
        response.raise_for_status()
        timings = response.json()["data"]["timings"]
        result = _parse_timings(timings)

        _cache_data[key] = result
        _cache_time[key] = now
        return result

    except Exception as e:
        logger.error(f"prayer for date {date_str} {city}: {e}")
        # fallback به امروز
        return get_prayer_times(city, country=country, method=method)
