"""Unified capability router for the Rooze Ziba AI.

The bot has many feature modules, while the AI uses a single tool registry.
This module is the bridge between those two worlds: it inventories the real
registered tools, exposes the media/handler capabilities that are executed by
Telegram handlers, and provides deterministic routing hints for live requests.
It deliberately does not implement feature logic; existing feature handlers
remain the source of truth.
"""
from __future__ import annotations

import re
from typing import Any


# These are capabilities handled by the Telegram media/message pipeline rather
# than by a text-only function call. They are still part of the AI contract.
HANDLER_CAPABILITIES: dict[str, tuple[str, ...]] = {
    "media": (
        "تحلیل تصویر و OCR",
        "ویرایش/تولید تصویر با درخواست متنی",
        "تحلیل ویدیو",
        "تحلیل فایل‌های PDF/DOCX/CSV/JSON/TXT",
        "جستجوی تصویری/Lens",
        "جستجوی خرید از روی عکس محصول",
        "گفتار به متن و ترجمه صدا",
        "تبدیل متن به صدا و پاسخ صوتی",
        "تولید موسیقی",
    ),
    "downloader": (
        "پردازش لینک و دانلود رسانه از مسیر downloader موجود ربات",
    ),
    "conversation": (
        "حافظه، تاریخچه، چندزبانه، بازنویسی، ترجمه و پاسخ طبیعی",
    ),
}

# Friendly group names for the actual registered tools. The mapping is based on
# the current registry names, so no duplicate business logic is introduced.
TOOL_GROUPS: dict[str, tuple[str, ...]] = {
    "زمان و تاریخ": ("get_current_datetime", "world_clock", "month_calendar", "convert_date", "calculate_age", "lunar_age", "birthday_countdown", "nowruz_countdown"),
    "آب‌وهوا و مکان": ("get_weather", "get_weather_forecast", "get_air_quality", "get_user_city", "hub_geocode", "hub_reverse_geocode", "city_distance", "world_distance", "qibla_direction", "get_prayer_times"),
    "بازار و مالی": ("get_market_prices", "get_crypto_price", "get_top_crypto", "convert_currency", "convert_crypto", "analyze_crypto", "crypto_chart_info", "get_economic_calendar", "ict_analysis", "v77_market_intelligence"),
    "خرید": ("search_shopping", "shopping_price_history", "hub_shopping_search"),
    "وب و اطلاعات زنده": ("web_search", "api_hub_call", "hub_smart_public_api", "hybrid_retrieve", "search_knowledge_base", "search_events"),
    "فیلم و سریال": ("hub_movie_tv_intelligence", "hub_movie_tv_latest"),
    "سرگرمی و محتوا": ("joke", "hafez_fal", "daily_verse_hadith", "fact_of_day", "daily_adhkar", "daily_challenge", "istikhara", "religious_countdown", "zodiac_animal"),
    "متن و ابزارهای عمومی": ("calculator", "count_text", "generate_password", "apply_font", "list_fonts"),
    "پروفایل و یادآوری": ("profile_summary", "create_reminder"),
    "عامل و اتوماسیون": ("run_workflow", "run_agent", "run_agent_v73", "run_agent_v74", "run_agent_v75", "run_agent_v76", "run_agent_v77", "multi_agent_v75"),
    "سلامت و امنیت داخلی": ("get_provider_health", "v73_health", "v74_system_status", "v75_system_status", "v76_system_status", "v77_system_status", "v75_security_scan", "v77_security_scan", "v75_news_score"),
}


def _registry() -> dict[str, dict[str, Any]]:
    # Lazy import prevents a circular dependency during ai_tools bootstrap.
    from bot.services.tool_runtime import _REGISTRY
    return _REGISTRY


def registered_tool_names() -> list[str]:
    return sorted(_registry().keys())


def capability_inventory() -> dict[str, Any]:
    registry = _registry()
    grouped: dict[str, list[str]] = {}
    assigned: set[str] = set()
    for group, names in TOOL_GROUPS.items():
        present = [name for name in names if name in registry]
        if present:
            grouped[group] = present
            assigned.update(present)

    other = sorted(set(registry) - assigned)
    if other:
        grouped["سایر قابلیت‌های ثبت‌شده"] = other

    return {
        "tool_count": len(registry),
        "groups": grouped,
        "handler_capabilities": {k: list(v) for k, v in HANDLER_CAPABILITIES.items()},
    }


def capability_contract() -> str:
    """Compact contract appended to the AI system prompt when tools are enabled."""
    inv = capability_inventory()
    chunks = [f"تعداد ابزارهای واقعی متصل به هسته AI: {inv['tool_count']}"]
    for group, names in inv["groups"].items():
        chunks.append(f"{group}: {', '.join(names)}")
    for group, values in inv["handler_capabilities"].items():
        chunks.append(f"مسیر {group} در handler: {'، '.join(values)}")
    return (
        "[AI CAPABILITY CONTRACT]\n"
        "این دستیار به قابلیت‌های واقعی زیر متصل است. برای داده یا عمل مربوط به این قابلیت‌ها، "
        "از ابزار/مسیر واقعی استفاده کن و قابلیت خیالی نساز. اگر درخواست چندبخشی است، می‌توانی "
        "چند ابزار را در یک نوبت یا workflow کوتاه ترکیب کنی. ابزارهای write/admin فقط با مجوز لازم اجرا می‌شوند.\n"
        + "\n".join(chunks)
    )


def _normalize(text: str) -> str:
    text = str(text or "").strip().replace("ي", "ی").replace("ك", "ک")
    return re.sub(r"[\u200c\u200f\u200e]+", " ", text)


def route_live_capability(prompt: str) -> str | None:
    """Return a deterministic tool for requests that must not use model memory."""
    q = _normalize(prompt)
    if not q:
        return None
    # Keep this tiny and deterministic. Detailed scoring remains in the generic
    # selector; these cases must never be answered from stale model knowledge.
    if re.search(r"(?:تاریخ\s*(?:دقیق|فعلی|الان|امروز)|امروز\s*چندمه|الان\s*(?:چه\s*)?تاریخ|current\s*(?:date|datetime)|today(?:\s*date)?)", q, re.I):
        return "get_current_datetime" if "get_current_datetime" in _registry() else None
    if re.search(r"(?:الان\s*(?:ساعت|چه\s*ساعتی)|ساعت\s*الان|what\s*time|current\s*time)", q, re.I):
        return "get_current_datetime" if "get_current_datetime" in _registry() else "world_clock"
    if re.search(r"(?:فیلم|سریال).*(?:جدید|تازه|آخرین|امسال|این\s*ماه)|(?:جدیدترین|آخرین)\s*(?:فیلم|سریال)", q, re.I):
        return "hub_movie_tv_latest" if "hub_movie_tv_latest" in _registry() else None
    if re.search(r"(?:قیمت|نرخ).*(?:بیت.?کوین|اتریوم|تتر|طلا|دلار|یورو|سکه)|(?:بیت.?کوین|اتریوم|تتر).*(?:قیمت|الان|فعلی)", q, re.I):
        for name in ("get_crypto_price", "get_market_prices"):
            if name in _registry():
                return name
    return None




FALLBACK_CAPABILITY_ORDER: tuple[str, ...] = (
    "hub_smart_public_api",
    "web_search",
)


def fallback_capability_tool() -> str | None:
    """Return the safest generic fallback tool available in the registry."""
    registry = _registry()
    for name in FALLBACK_CAPABILITY_ORDER:
        if name in registry:
            return name
    return None


def route_with_fallback(prompt: str) -> str | None:
    """Route known requests first, then use public API/Web fallback."""
    direct = route_live_capability(prompt)
    if direct:
        return direct
    q = _normalize(prompt)
    if not q:
        return None
    registry = _registry()
    ranked: list[tuple[float, int, str]] = []
    for name, entry in registry.items():
        if name in FALLBACK_CAPABILITY_ORDER:
            continue
        score = 0.0
        hits = 0
        for kw in entry.get("keywords") or ():
            try:
                m = re.search(kw, q, re.I)
            except re.error:
                continue
            if m:
                hits += 1
                score += 1.0 + min(len(m.group(0)), 64) / 16.0
        if hits:
            ranked.append((score, hits, name))
    if ranked:
        ranked.sort(reverse=True)
        best = ranked[0]
        if best[0] >= 2.25 or best[1] >= 2:
            return best[2]
    return fallback_capability_tool()


def ai_capability_catalog() -> str:
    """Human-readable inventory used when the user asks what the bot can do."""
    inv = capability_inventory()
    lines = [f"تعداد قابلیت‌های ابزاری متصل: {inv['tool_count']}", ""]
    for group, names in inv["groups"].items():
        lines.append(f"🔹 {group}: {', '.join(names)}")
    lines.append("")
    lines.append("🔹 مسیرهای رسانه‌ای متصل: " + "، ".join(sum(inv["handler_capabilities"].values(), [])))
    return "\n".join(lines)
