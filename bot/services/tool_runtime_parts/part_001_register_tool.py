from typing import Callable
from typing import List
from typing import Optional

# Auto-split part 1: register_tool
def register_tool(
    name: str,
    description: str,
    parameters: Optional[dict] = None,
    handler: Optional[Callable] = None,
    *,
    keywords: Optional[List[str]] = None,
    risk: str = "read",
    network: bool = False,
) -> None:
    """ثبت یک ابزار برای AI. keywords برای تزریق خودکار وقتی مدل tool ندارد."""
    if not name or not handler:
        raise ValueError("name و handler الزامی‌اند")
    _REGISTRY[name] = {
        "name": name,
        "description": description,
        "parameters": parameters or {"type": "object", "properties": {}},
        "handler": handler,
        "keywords": keywords or [],
        "cacheable": False,
        "risk": risk if risk in {"read", "write", "admin"} else "read",
        "network": bool(network),
    }
    logger.debug("AI tool registered: %s", name)
