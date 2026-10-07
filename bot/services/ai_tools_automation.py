"""ai_tools: automation responsibilities."""
from .ai_tools_common import *  # noqa: F401,F403
from . import ai_tools_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def _tool_reminder(
    text: str = "",
    remind_at: str = "",
    repeat_type: str = "once",
    repeat_every: int = 0,
    user_id: int = 0,
) -> str:
    from bot.database import add_reminder
    repeat_type = repeat_type or "once"
    repeat_every = max(0, int(repeat_every or 0))
    add_reminder(
        user_id, text, remind_at,
        repeat_type=repeat_type,
        repeat_every=repeat_every,
    )
    return f"یادآوری ثبت شد: {text} در {remind_at}"

async def _tool_ict_analysis(symbol: str = "btc", interval: str = "1h", user_id: int = 0) -> str:
    from bot.features.market.finance_ict import analyze_ict
    return await analyze_ict(symbol or "btc", interval=interval or "1h")
