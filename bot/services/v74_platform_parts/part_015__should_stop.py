from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from bot.services.v74_platform import AgentStep

# Auto-split part 15: _should_stop
def _should_stop(goal: str, step: AgentStep, result: str) -> bool:
    low = (goal + " " + result).lower()
    if any(x in low for x in ("فقط", "تنها", "just", "only")) and step.reason in {"market", "weather", "air_quality", "calendar"}:
        return True
    return bool(result) and not str(result).startswith(("خطا", "ابزار ناشناخته", "ابزار مسدود", "زمان اجرای")) and step.reason in {"weather", "air_quality"}
