"""High-level API Hub helpers used by bot features and AI tools."""
from __future__ import annotations

from typing import Any

from .api_hub import api_hub


async def api_call(provider: str, params: dict[str, Any] | None = None) -> Any:
    return await api_hub.call(provider, params=params)


async def get_weather(latitude: float, longitude: float, *, forecast_days: int = 3) -> dict[str, Any]:
    return await api_hub.call(
        "open_meteo_forecast",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "forecast_days": max(1, min(int(forecast_days), 16)),
            "timezone": "auto",
        },
    )


async def get_exchange_rate(base: str = "USD", target: str = "EUR") -> dict[str, Any]:
    return await api_hub.call("frankfurter", params={"from": base.upper(), "to": target.upper()})


async def get_country(name: str) -> Any:
    return await api_hub.call("rest_countries", params={"name": name})


async def search_books(query: str, *, limit: int = 10) -> dict[str, Any]:
    return await api_hub.call(
        "open_library_search",
        params={"q": query, "limit": max(1, min(int(limit), 50))},
    )


async def get_random_joke() -> dict[str, Any]:
    return await api_hub.call("jokeapi", params={"safe-mode": "true", "type": "single,twopart"})


async def search_products(
    query: str, *, country: str = "US", language: str = "en", max_results: int = 10,
    min_price: float | None = None, max_price: float | None = None, free_shipping: bool | None = None,
) -> Any:
    """Search real AliExpress listings through the keyless OneFindMe API."""
    q = str(query or "").strip()
    if not q:
        raise ValueError("query is required")
    params: dict[str, Any] = {
        "query": q,
        "country": str(country or "US").upper(),
        "language": str(language or "en").lower(),
        "max_results": max(1, min(int(max_results), 20)),
    }
    if min_price is not None:
        params["min_price"] = max(0.0, float(min_price))
    if max_price is not None:
        params["max_price"] = max(0.0, float(max_price))
    if free_shipping is not None:
        params["free_shipping"] = bool(free_shipping)
    return await api_hub.call("onefindme_search", params=params)


async def geocode(query: str, *, limit: int = 5, language: str = "fa") -> Any:
    q = str(query or "").strip()
    if not q:
        raise ValueError("query is required")
    return await api_hub.call(
        "nominatim_search",
        params={
            "q": q, "format": "jsonv2", "addressdetails": 1,
            "limit": max(1, min(int(limit), 10)), "accept-language": language or "fa",
        },
    )


async def reverse_geocode(latitude: float, longitude: float, *, language: str = "fa") -> Any:
    return await api_hub.call(
        "nominatim_reverse",
        params={
            "lat": float(latitude), "lon": float(longitude), "format": "jsonv2",
            "addressdetails": 1, "accept-language": language or "fa",
        },
    )


async def search_scientific_literature(query: str, *, limit: int = 10) -> dict[str, Any]:
    q = str(query or "").strip()
    if not q:
        raise ValueError("query is required")
    return await api_hub.call(
        "europe_pmc_search",
        params={"query": q, "format": "json", "pageSize": max(1, min(int(limit), 50)), "resultType": "lite"},
    )


async def search_species(query: str, *, limit: int = 10) -> dict[str, Any]:
    q = str(query or "").strip()
    if not q:
        raise ValueError("query is required")
    return await api_hub.call(
        "gbif_species_search",
        params={"q": q, "limit": max(1, min(int(limit), 50))},
    )


async def search_clinical_trials(query: str, *, limit: int = 10) -> dict[str, Any]:
    q = str(query or "").strip()
    if not q:
        raise ValueError("query is required")
    return await api_hub.call(
        "clinical_trials_search",
        params={"query.term": q, "pageSize": max(1, min(int(limit), 50)), "format": "json"},
    )


async def search_cves(keyword: str | None = None, *, cve_id: str | None = None, limit: int = 10) -> dict[str, Any]:
    params: dict[str, Any] = {"resultsPerPage": max(1, min(int(limit), 20))}
    if cve_id:
        params["cveId"] = str(cve_id).strip().upper()
    elif keyword:
        params["keywordSearch"] = str(keyword).strip()
    else:
        raise ValueError("keyword or cve_id is required")
    return await api_hub.call("nvd_cves", params=params)


async def open_data(
    *, data_type: str, drilldowns: str | None = None, measures: str | None = None,
    year: int | str | None = None, filters: str | None = None, limit: int = 20,
) -> dict[str, Any]:
    params: dict[str, Any] = {"Geography": "04000US06" if data_type.lower() == "Population" else None}
    params = {k: v for k, v in params.items() if v is not None}
    params["drilldowns"] = drilldowns or "Nation"
    params["measures"] = measures or data_type
    if year is not None:
        params["year"] = str(year)
    if filters:
        params["properties"] = filters
    params["limit"] = max(1, min(int(limit), 100))
    return await api_hub.call("datausa", params=params)
