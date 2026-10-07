"""Late registration/compatibility actions for ai_tools."""
from .ai_tools_common import *  # noqa
from . import ai_tools_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


register_tool(
    name="run_workflow",
    description="اجرای یک برنامه چندمرحله‌ای کوتاه با ابزارهای موجود. فقط وقتی چند ابزار باید به‌ترتیب اجرا شوند استفاده کن؛ حداکثر 4 مرحله. برای ارجاع به خروجی مرحله قبل از $step1، $step2 و ... استفاده کن.",
    parameters={
        "type": "object",
        "properties": {
            "steps": {
                "type": "array",
                "maxItems": 4,
                "items": {
                    "type": "object",
                    "properties": {
                        "tool": {"type": "string"},
                        "arguments": {"type": "object"},
                    },
                    "required": ["tool"],
                },
            }
        },
        "required": ["steps"],
    },
    handler=_run_workflow_async,
)

register_tool(
    name="run_agent",
    description=(
        "دستیار برنامه‌ریز محدود: برای هدف‌های چندبخشی، ابزارهای موجود را خودش انتخاب و به‌ترتیب اجرا می‌کند "
        "و حداکثر یک بار مسیر امن را ترمیم می‌کند. برای اطلاعات فعلی می‌تواند retrieval وب را فعال کند. "
        "حلقه بی‌نهایت ندارد و حداکثر 4 مرحله اجرا می‌شود."
    ),
    parameters={
        "type": "object",
        "properties": {"goal": {"type": "string", "description": "هدف کامل کاربر"}},
        "required": ["goal"],
    },
    handler=_run_agent,
    keywords=[r"خودت.*برنامه|چندمرحله|دستیار.*هوشمند|agent|برنامه.?ریزی.*هوشمند"],
)

_register_builtin_tools()

register_tool(
    name="get_provider_health",
    description=(
        "گزارش داخلی و بدون کلید از سلامت Providerهای AI بر اساس موفقیت، خطا، latency و cooldown اخیر. "
        "برای عیب‌یابی و تشخیص اینکه کدام Provider مشکل دارد استفاده کن؛ هیچ درخواست آزمایشی شبکه‌ای ارسال نمی‌کند."
    ),
    parameters={"type": "object", "properties": {}},
    handler=_provider_health,
    keywords=[r"سلامت.*(?:provider|پرووایدر|مدل)", r"وضعیت.*(?:ai|هوش مصنوعی|مدل)", r"عیب.?یابی.*(?:ai|هوش مصنوعی)", r"provider health", r"diagnostic"],
)

register_tool(
    name="search_knowledge_base",
    description="جستجوی هوشمند در مستندات داخلی و عمومی پروژه ربات. برای پرسش درباره قابلیت‌ها، تنظیمات و نحوه کار خود ربات استفاده کن؛ اطلاعات نامرتبط یا jokes_data.json در این شاخص وجود ندارد.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "عبارت جستجو"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 6},
        },
        "required": ["query"],
    },
    handler=_knowledge_search,
    keywords=[r"پایگاه دانش|مستندات ربات|راهنمای ربات|تنظیمات ربات|قابلیت.*ربات|knowledge base|documentation"],
)

register_tool(
    name="hybrid_retrieve",
    description=(
        "ترکیب حافظه مرتبط کاربر و پایگاه دانش داخلی؛ در صورت نیاز و با include_web=true "
        "از جستجوی وب هم استفاده می‌کند. برای اطلاعات فعلی/قیمت/اخبار می‌تواند وب را فعال کند. "
        "در حالت عادی درخواست شبکه‌ای انجام نمی‌دهد."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "include_web": {"type": "boolean", "description": "آیا جستجوی وب هم انجام شود؟"},
        },
        "required": ["query"],
    },
    handler=_hybrid_retrieve,
    keywords=[r"ترکیب.*منبع|حافظه.*مستندات|منابع.*مرتبط|اطلاعات.*فعلی|hybrid retrieval|rag"],
)

TOOL_DEFINITIONS = _ToolDefsProxy()

register_tool(
    name="run_agent_v73",
    description="Agent حرفه‌ای محدود با برنامه‌ریزی چندابزاری، بودجه اجرا، جلوگیری از تکرار، تعمیر امن و ثبت trace. عملیات نوشتنی بدون تأیید اجرا نمی‌شوند.",
    parameters={"type":"object","properties":{"goal":{"type":"string"}},"required":["goal"]},
    handler=_run_agent_v73,
    keywords=[r"agent حرفه.?ای", r"عامل هوشمند", r"چند.?ابزاری", r"autonomous agent", r"tool architecture"],
)

register_tool(name="v73_health", description="گزارش سلامت، circuit protection و performance داخلی بدون اطلاعات محرمانه.", parameters={"type":"object","properties":{}}, handler=_v73_health, keywords=[r"سلامت سیستم", r"performance", r"self healing", r"خود.?ترمیم"])

register_tool(
    name="run_agent_v74",
    description="Agent 2.0 محدود و امن برای برنامه‌ریزی پویا، انتخاب ابزار، توقف هوشمند و repair کنترل‌شده.",
    parameters={"type":"object","properties":{"goal":{"type":"string"}},"required":["goal"]},
    handler=_run_agent_v74, keywords=[r"agent 2", r"عامل هوشمند", r"اجرای چندمرحله", r"برنامه.?ریزی هوشمند"]
)

register_tool(
    name="v74_system_status",
    description="گزارش امن سلامت، ابزارها، عملکرد، providerها، persistence و runtime نسخه V74.",
    parameters={"type":"object","properties":{}}, handler=_v74_system_status,
    keywords=[r"سلامت v74", r"وضعیت v74", r"observability", r"reliability"]
)

register_tool(
    name="run_agent_v75",
    description="Agent 3.0 محدود با بودجه اجرا، جلوگیری از تکرار، امنیت و اجرای ابزارهای تخصصی موجود.",
    parameters={"type":"object","properties":{"goal":{"type":"string"}},"required":["goal"]},
    handler=_run_agent_v75, keywords=[r"agent 3",r"agent 3.0",r"عامل.*پیشرفته",r"برنامه.?ریزی چندمرحله"]
)

register_tool(
    name="multi_agent_v75",
    description="هماهنگی محدود چند متخصص برای پژوهش، بازار، اقتصاد و ابزارهای عمومی؛ بدون حلقه مستقل و بی‌نهایت.",
    parameters={"type":"object","properties":{"goal":{"type":"string"}},"required":["goal"]},
    handler=_multi_agent_v75, keywords=[r"multi.?agent",r"چند عامل",r"چند متخصص"]
)

register_tool(name="v75_system_status", description="گزارش امن وضعیت V75 شامل امنیت، workflow، alert، memory و performance.", parameters={"type":"object","properties":{}}, handler=_v75_status, keywords=[r"سلامت v75",r"وضعیت v75",r"داشبورد v75"])

register_tool(name="v75_security_scan", description="اسکن امن متن برای prompt injection، افشای secret و الگوهای command خطرناک.", parameters={"type":"object","properties":{"text":{"type":"string"}},"required":["text"]}, handler=_v75_security, keywords=[r"security scan",r"اسکن امنیتی",r"prompt injection"])

register_tool(name="v75_news_score", description="امتیازدهی اولیه sentiment و impact خبر بدون ادعای صحت منبع.", parameters={"type":"object","properties":{"title":{"type":"string"},"content":{"type":"string"}},"required":["title"]}, handler=_v75_news_score, keywords=[r"تحلیل خبر",r"sentiment خبر",r"impact خبر"])

register_tool(name="run_agent_v76", description="Agent 4.0 محدود با Intent، برنامه‌ریزی، Verify و بودجه اجرای امن.", parameters={"type":"object","properties":{"goal":{"type":"string"}},"required":["goal"]}, handler=_run_agent_v76, keywords=[r"agent 4",r"عامل 4",r"برنامه.?ریزی پیشرفته",r"adaptive agent"])

register_tool(name="v76_system_status", description="وضعیت امن هسته Adaptive V76، امنیت، Agent، Job، Cache و Provider Mesh.", parameters={"type":"object","properties":{}}, handler=_v76_status, keywords=[r"سلامت v76",r"وضعیت v76",r"adaptive core"])

try:
    register_tool(
        name="run_agent_v77",
        description="Agent 5.0 با برنامه‌ریزی وابسته، اجرای محدود، Verify و Retry امن.",
        parameters={"type":"object","properties":{"goal":{"type":"string"}},"required":["goal"]},
        handler=_run_agent_v77,
        keywords=[r"agent 5",r"عامل 5",r"برنامه.?ریزی چندمرحله.?ای"]
    )
    register_tool(
        name="v77_system_status",
        description="وضعیت امن هسته V77 Ultimate.",
        parameters={"type":"object","properties":{}}, handler=_v77_status,
        keywords=[r"سلامت v77",r"وضعیت v77",r"ultimate status"]
    )
    register_tool(
        name="v77_market_intelligence",
        description="تحلیل پیشرفته روند، EMA، RSI، مومنتوم و نوسان.",
        parameters={"type":"object","properties":{"closes":{"type":"array","items":{"type":"number"}}}}, handler=_v77_market
    )
    register_tool(
        name="v77_security_scan",
        description="اسکن امنیتی ورودی بدون افشای جزئیات داخلی.",
        parameters={"type":"object","properties":{"text":{"type":"string"}},"required":["text"]}, handler=_v77_security
    )
except Exception:
    pass

try:
    from bot.services.api_hub import api_hub_ai as _api_hub_ai  # noqa: F401,E402
except Exception:
    pass

try:
    from bot.services.ai_capability_router import ai_capability_catalog as _ai_capability_catalog

    _register_tool(
        name="ai_capability_catalog",
        description="فهرست قابلیت‌های واقعی و متصل به دستیار هوشمند؛ فقط وقتی کاربر درباره امکانات ربات/دستیار می‌پرسد استفاده کن.",
        parameters={"type": "object", "properties": {}},
        handler=_ai_capability_catalog,
        keywords=[r"قابلیت.?های? ربات", r"چه کارهایی می.?تونی", r"چه قابلیت", r"امکانات ربات", r"توانایی.?های? تو"],
        risk="read",
    )
except Exception:
    pass

try:
    from bot.services.capability_autoload import ensure_all_capabilities_registered

    ensure_all_capabilities_registered()
except Exception as _cap_exc:  # never break AI import path
    try:
        from bot.logger import logger as _lg
        _lg.warning("capability autoload failed: %s", _cap_exc)
    except Exception:
        pass
