# Auto-split part 8: geocode
async def geocode(place: str):
    """(lat, lon, display_name) یا None"""
    place_raw = (place or "").strip()
    if not place_raw:
        return None
    key = _norm_place(place_raw)
    if key in _geo_cache:
        return _geo_cache[key]

    # ۱) لیست داخلی — فقط match دقیق
    if key in KNOWN_PLACES:
        lat, lon, short = KNOWN_PLACES[key]
        _geo_cache[key] = (lat, lon, short)
        return lat, lon, short
    if key in COUNTRY_CENTERS:
        lat, lon, short = COUNTRY_CENTERS[key]
        _geo_cache[key] = (lat, lon, short)
        return lat, lon, short

    headers = {"User-Agent": "ALIMJBot/2.2 (telegram-bot; distance)"}
    try:
        async with httpx.AsyncClient(timeout=15.0, headers=headers, follow_redirects=True) as client:
            # ۲) Open-Meteo Geocoding (دقیق و پایدار)
            try:
                r = await client.get(
                    "https://geocoding-api.open-meteo.com/v1/search",
                    params={"name": place_raw, "count": 5, "language": "fa"},
                )
                if r.status_code == 200:
                    results = (r.json() or {}).get("results") or []
                    if results:
                        # ترجیح ایران/منطقه اگر چند نتیجه
                        best = results[0]
                        for item in results:
                            cc = (item.get("country_code") or "").upper()
                            if cc in ("IR", "IQ", "TR", "AF", "SA", "AE", "SY", "LB"):
                                # اگر کوئری فارسی است اولویت خاورمیانه
                                if any("\u0600" <= ch <= "\u06FF" for ch in place_raw):
                                    best = item
                                    break
                        lat = float(best["latitude"])
                        lon = float(best["longitude"])
                        name = best.get("name") or place_raw
                        country = best.get("country") or ""
                        short = f"{name}، {country}" if country else name
                        _geo_cache[key] = (lat, lon, short)
                        return lat, lon, short
            except Exception as e:
                logger.warning(f"open-meteo geo: {e}")

            # ۳) Nominatim
            queries = [place_raw]
            if not any(x in key for x in ("iran", "ایران", ",")):
                queries.append(f"{place_raw}, Iran")
            for q in queries:
                try:
                    r = await client.get(
                        "https://nominatim.openstreetmap.org/search",
                        params={
                            "q": q,
                            "format": "json",
                            "limit": 5,
                            "accept-language": "fa,en",
                        },
                    )
                    if r.status_code != 200:
                        continue
                    results = r.json() or []
                    if not results:
                        continue

                    def score(item):
                        t = (item.get("type") or "").lower()
                        cls = (item.get("class") or "").lower()
                        imp = float(item.get("importance") or 0)
                        bonus = 0
                        if t in ("city", "town", "municipality", "administrative", "country", "state"):
                            bonus += 3
                        if cls in ("place", "boundary"):
                            bonus += 1
                        dn = (item.get("display_name") or "").lower()
                        if any(x in dn for x in ("village", "hamlet", "روستا", "دهستان", "بخش")):
                            bonus -= 4
                        return imp + bonus

                    results.sort(key=score, reverse=True)
                    best = results[0]
                    lat = float(best["lat"])
                    lon = float(best["lon"])
                    short = _short_name(best.get("display_name") or place_raw, place_raw)
                    _geo_cache[key] = (lat, lon, short)
                    return lat, lon, short
                except Exception:
                    continue

            # ۴) Photon
            try:
                r = await client.get(
                    "https://photon.komoot.io/api/",
                    params={"q": place_raw, "limit": 3},
                )
                if r.status_code == 200:
                    for f in (r.json() or {}).get("features") or []:
                        coords = f.get("geometry", {}).get("coordinates") or []
                        props = f.get("properties") or {}
                        if len(coords) < 2:
                            continue
                        nm = props.get("name") or place_raw
                        country = props.get("country") or ""
                        city = props.get("city") or props.get("state") or nm
                        short = f"{city}، {country}" if country else city
                        _geo_cache[key] = (float(coords[1]), float(coords[0]), short)
                        return _geo_cache[key]
            except Exception:
                pass
    except Exception as e:
        logger.error(f"geocode [{place_raw}]: {e}")
    return None
