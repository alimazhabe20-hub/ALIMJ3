"""Calendar helpers with Tehran/Baghdad local-day handling and live Hijri API."""

from __future__ import annotations

from datetime import date, datetime
from functools import lru_cache
from typing import Any

import jdatetime
import pytz
import requests
from hijri_converter import Gregorian

from bot.utils.events import shamsi_events, hijri_events

HIJRI_API = "https://theshia.org/api/v1/hijri"

# The bot currently exposes Iran/Iraq as selectable countries.
# The API has an official Iran calendar and a global moonsighting mode;
# for Iraq we deliberately use moonsighting rather than pretending there
# is an Iraq-specific official table in this API.
COUNTRY_TIMEZONES = {
    "Iran": "Asia/Tehran",
    "ایران": "Asia/Tehran",
    "Iraq": "Asia/Baghdad",
    "عراق": "Asia/Baghdad",
}

HIJRI_MONTHS_FA = {
    1: "محرم", 2: "صفر", 3: "ربیع‌الاول", 4: "ربیع‌الثانی",
    5: "جمادی‌الاول", 6: "جمادی‌الثانی", 7: "رجب", 8: "شعبان",
    9: "رمضان", 10: "شوال", 11: "ذی‌قعده", 12: "ذی‌الحجه",
}


def get_country_timezone(country: str | None = None) -> str:
    return COUNTRY_TIMEZONES.get(str(country or "Iran").strip(), "Asia/Tehran")


def get_hijri_calendar(country: str | None = None) -> str:
    """Select the API reckoning appropriate to the configured country."""
    value = str(country or "Iran").strip().lower()
    if value in {"iraq", "عراق"}:
        return "moonsighting"
    return "iran"


def get_today_local(country: str | None = None) -> jdatetime.date:
    tz = pytz.timezone(get_country_timezone(country))
    now = datetime.now(tz)
    return jdatetime.datetime.fromgregorian(datetime=now).date()


def get_today_tehran():
    """Backward-compatible helper used by older handlers."""
    return get_today_local("Iran")


@lru_cache(maxsize=256)
def _fetch_hijri(gregorian_iso: str, calendar: str) -> dict[str, Any] | None:
    try:
        response = requests.get(
            HIJRI_API,
            params={"date": gregorian_iso, "calendar": calendar},
            timeout=(3.0, 6.0),
            headers={"User-Agent": "RoozeZiba/Calendar"},
        )
        response.raise_for_status()
        data = response.json()
        hijri = data.get("hijri") or {}
        if not all(k in hijri for k in ("year", "month", "day")):
            return None
        return data
    except Exception:
        return None


def _fallback_hijri(g_date: date) -> dict[str, Any]:
    hijri = Gregorian(g_date.year, g_date.month, g_date.day).to_hijri()
    name = HIJRI_MONTHS_FA.get(hijri.month, "نامشخص")
    return {
        "day": hijri.day,
        "month": hijri.month,
        "month_name": name,
        "year": hijri.year,
        "full": f"{hijri.day} {name} {hijri.year}",
        "calendar": "fallback",
        "source": "hijri_converter",
    }


def get_hijri_date(g_date, country: str | None = None):
    """Convert a Gregorian date using the selected country's calendar basis.

    Iran -> official Iranian reckoning.
    Iraq -> global moonsighting mode (the API currently does not expose an
    Iraq-specific official table).
    """
    try:
        if hasattr(g_date, "date") and not isinstance(g_date, date):
            g_date = g_date.date()
        g_date = date(g_date.year, g_date.month, g_date.day)
        calendar = get_hijri_calendar(country)
        data = _fetch_hijri(g_date.isoformat(), calendar)
        if data:
            h = data["hijri"]
            month = int(h["month"])
            day = int(h["day"])
            year = int(h["year"])
            name = (data.get("monthName") or {}).get("fa") or HIJRI_MONTHS_FA.get(month, "نامشخص")
            return {
                "day": day,
                "month": month,
                "month_name": name,
                "year": year,
                "full": f"{day} {name} {year}",
                "calendar": data.get("calendarUsed", calendar),
                "source": data.get("source", "api"),
            }
        return _fallback_hijri(g_date)
    except Exception:
        return {"day": 0, "month": 0, "month_name": "نامشخص", "year": 0, "full": "نامشخص", "calendar": "error", "source": "error"}


def get_shamsi_events(year, month, day):
    key = f"{month}-{day}"
    return shamsi_events.get(key, ["هیچ مناسبت خاصی ثبت نشده است."])


def get_hijri_events(hijri_month, hijri_day):
    key = f"{hijri_month}-{hijri_day}"
    return hijri_events.get(key, ["هیچ مناسبت قمری خاصی ثبت نشده است."])
