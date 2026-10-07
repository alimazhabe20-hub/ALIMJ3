from typing import List

# Auto-split part 3: get_tool_definitions
def get_tool_definitions() -> List[dict]:
    """لیست tools به فرمت OpenAI/Groq."""
    out = []
    for t in _REGISTRY.values():
        out.append(
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["parameters"],
                },
            }
        )
    return out
