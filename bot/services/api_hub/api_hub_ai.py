"""Optional AI-tool bridge for the keyless API Hub.

Imported by the stable ai_tools facade. It adds one generic, read-only tool
instead of adding a large number of Telegram buttons.
"""
from __future__ import annotations

from bot.services.tool_runtime import register_tool
from bot.services.api_hub import (
    api_call, list_providers, search_products, geocode, reverse_geocode,
    search_scientific_literature, search_species, search_clinical_trials,
    search_cves, open_data,
)


def _provider_names() -> str:
    return ", ".join(item.name for item in list_providers())


async def _api_hub_call(provider: str, params: dict | None = None):
    return await api_call(provider, params or {})


register_tool(
    name="api_hub_call",
    description=(
        "اجرای API عمومی بدون API key از API Hub. فقط providerهای ثبت‌شده و read-only را اجرا می‌کند. "
        f"Providerهای فعال: {_provider_names()}"
    ),
    parameters={
        "type": "object",
        "properties": {
            "provider": {"type": "string", "description": "نام provider ثبت‌شده"},
            "params": {"type": "object", "description": "پارامترهای query/path"},
        },
        "required": ["provider"],
    },
    handler=_api_hub_call,
    keywords=[r"api hub", r"api عمومی", r"public api", r"اطلاعات عمومی"],
    risk="read",
    network=True,
)


async def _shopping_search(query: str, country: str = "US", language: str = "en", max_results: int = 10, min_price: float | None = None, max_price: float | None = None, free_shipping: bool | None = None):
    return await search_products(
        query, country=country, language=language, max_results=max_results,
        min_price=min_price, max_price=max_price, free_shipping=free_shipping,
    )


async def _geocode(query: str, limit: int = 5, language: str = "fa"):
    return await geocode(query, limit=limit, language=language)


async def _reverse_geocode(latitude: float, longitude: float, language: str = "fa"):
    return await reverse_geocode(latitude, longitude, language=language)


register_tool(
    name="hub_shopping_search",
    description="جست‌وجوی کالای واقعی در AliExpress از طریق OneFindMe؛ قیمت، امتیاز، تعداد سفارش و لینک را برمی‌گرداند.",
    parameters={"type": "object", "properties": {
        "query": {"type": "string"}, "country": {"type": "string", "default": "US"},
        "language": {"type": "string", "default": "en"}, "max_results": {"type": "integer", "default": 10},
        "min_price": {"type": "number"}, "max_price": {"type": "number"},
        "free_shipping": {"type": "boolean"},
    }, "required": ["query"]},
    handler=_shopping_search,
    keywords=[r"خرید", r"قیمت کالا", r"محصول", r"shopping", r"product search", r"کفش", r"لباس"],
    risk="read", network=True,
)

register_tool(
    name="hub_geocode",
    description="تبدیل نام مکان یا آدرس به مختصات جغرافیایی با Nominatim/OpenStreetMap.",
    parameters={"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 5}, "language": {"type": "string", "default": "fa"}}, "required": ["query"]},
    handler=_geocode, keywords=[r"موقعیت", r"مختصات", r"آدرس", r"geocode", r"coordinates"], risk="read", network=True,
)

register_tool(
    name="hub_reverse_geocode",
    description="تبدیل latitude/longitude به آدرس و نام مکان.",
    parameters={"type": "object", "properties": {"latitude": {"type": "number"}, "longitude": {"type": "number"}, "language": {"type": "string", "default": "fa"}}, "required": ["latitude", "longitude"]},
    handler=_reverse_geocode, keywords=[r"reverse geocode", r"آدرس مختصات"], risk="read", network=True,
)


async def _science_search(query: str, limit: int = 10):
    return await search_scientific_literature(query, limit=limit)

async def _species_search(query: str, limit: int = 10):
    return await search_species(query, limit=limit)

async def _clinical_trials(query: str, limit: int = 10):
    return await search_clinical_trials(query, limit=limit)

async def _cve_search(keyword: str | None = None, cve_id: str | None = None, limit: int = 10):
    return await search_cves(keyword, cve_id=cve_id, limit=limit)

async def _open_data(data_type: str, drilldowns: str = "Nation", measures: str | None = None, year: int | None = None, filters: str | None = None, limit: int = 20):
    return await open_data(data_type=data_type, drilldowns=drilldowns, measures=measures, year=year, filters=filters, limit=limit)

register_tool(
    name="hub_science_search", description="جست‌وجوی مقالات علمی و پزشکی در Europe PMC.",
    parameters={"type":"object","properties":{"query":{"type":"string"},"limit":{"type":"integer","default":10}},"required":["query"]},
    handler=_science_search, keywords=[r"مقاله علمی",r"تحقیق",r"science",r"paper",r"پژوهش"], risk="read", network=True,
)
register_tool(
    name="hub_species_search", description="جست‌وجوی گونه‌ها و داده‌های تنوع زیستی در GBIF.",
    parameters={"type":"object","properties":{"query":{"type":"string"},"limit":{"type":"integer","default":10}},"required":["query"]},
    handler=_species_search, keywords=[r"گونه",r"حیوان",r"گیاه",r"species",r"biodiversity"], risk="read", network=True,
)
register_tool(
    name="hub_clinical_trials", description="جست‌وجوی مطالعات و کارآزمایی‌های بالینی در ClinicalTrials.gov؛ نتیجه جایگزین تشخیص پزشکی نیست.",
    parameters={"type":"object","properties":{"query":{"type":"string"},"limit":{"type":"integer","default":10}},"required":["query"]},
    handler=_clinical_trials, keywords=[r"clinical trial",r"کارآزمایی بالینی",r"مطالعه پزشکی",r"clinicaltrials"], risk="read", network=True,
)
register_tool(
    name="hub_security_cve", description="جست‌وجوی آسیب‌پذیری‌های CVE در NVD؛ داده امنیتی است و اجرای حمله انجام نمی‌دهد.",
    parameters={"type":"object","properties":{"keyword":{"type":"string"},"cve_id":{"type":"string"},"limit":{"type":"integer","default":10}}},
    handler=_cve_search, keywords=[r"CVE",r"آسیب پذیری",r"vulnerability",r"NVD",r"امنیت"], risk="read", network=True,
)
register_tool(
    name="hub_open_data", description="دریافت داده‌های عمومی اقتصادی و جمعیتی از Data USA.",
    parameters={"type":"object","properties":{"data_type":{"type":"string"},"drilldowns":{"type":"string","default":"Nation"},"measures":{"type":"string"},"year":{"type":"integer"},"filters":{"type":"string"},"limit":{"type":"integer","default":20}},"required":["data_type"]},
    handler=_open_data, keywords=[r"داده عمومی",r"open data",r"آمار",r"جمعیت",r"اقتصاد"], risk="read", network=True,
)
