# Auto-split part 10: _specialist_for
def _specialist_for(tool: str) -> str:
    if "market" in tool: return "finance"
    if "calendar" in tool: return "economics"
    if "search" in tool or "retrieve" in tool: return "research"
    if "weather" in tool: return "utility"
    return "general"
