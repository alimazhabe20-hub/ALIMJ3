# Auto-split part 2: get_registered_tool_names
def get_registered_tool_names() -> set[str]:
    """Return a snapshot of registered tool names for workflow validation."""
    return set(_REGISTRY)
