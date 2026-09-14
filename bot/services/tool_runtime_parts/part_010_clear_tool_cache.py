# Auto-split part 10: clear_tool_cache
def clear_tool_cache() -> None:
    """Clear read-through tool cache without touching tool registry/state."""
    _TOOL_CACHE.clear()
