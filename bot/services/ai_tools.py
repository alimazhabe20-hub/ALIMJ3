"""Stable public facade.

IMPORTANT: Keep this file small and stable. New functionality belongs in the
secondary ``ai_tools_parts/`` modules. The complete legacy implementation is kept
unchanged in ``ai_tools_parts/part_999_core_legacy.py`` for compatibility.
"""
from bot.utils.modular_loader import load_modular_part

load_modular_part(__file__, 'ai_tools_parts/part_999_core_legacy.py')

# Keyless Public API Hub bridge. Kept outside the legacy implementation.
from bot.services.api_hub import api_hub_ai as _api_hub_ai  # noqa: F401,E402

# Unified capability catalog: lets the model inspect the real tool/handler
# surface instead of assuming that only the visible Telegram buttons exist.
from bot.services.ai_capability_router import ai_capability_catalog as _ai_capability_catalog
from bot.services.tool_runtime import register_tool as _register_tool

_register_tool(
    name="ai_capability_catalog",
    description="فهرست قابلیت‌های واقعی و متصل به دستیار هوشمند؛ فقط وقتی کاربر درباره امکانات ربات/دستیار می‌پرسد استفاده کن.",
    parameters={"type": "object", "properties": {}},
    handler=_ai_capability_catalog,
    keywords=[r"قابلیت.?های? ربات", r"چه کارهایی می.?تونی", r"چه قابلیت", r"امکانات ربات", r"توانایی.?های? تو"],
    risk="read",
)

