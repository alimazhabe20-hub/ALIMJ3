from typing import Any

# Auto-split part 5: sanitize_tool_arguments
def sanitize_tool_arguments(args: dict[str, Any], *, max_text=6000) -> dict[str, Any]:
    """Bound agent/tool input without altering normal handler semantics."""
    out: dict[str, Any] = {}
    for key, value in (args or {}).items():
        if isinstance(value, str):
            out[key] = value[:max_text]
        elif isinstance(value, (int, float, bool)) or value is None:
            out[key] = value
        elif isinstance(value, list):
            out[key] = value[:20]
        elif isinstance(value, dict):
            out[key] = sanitize_tool_arguments(value, max_text=max_text // 2)
        else:
            out[key] = str(value)[:max_text]
    return out
