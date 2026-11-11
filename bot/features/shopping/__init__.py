"""Shopping feature package.

Public API stays stable:
  from bot.features.shopping import search_shopping, compare_products, ...
Also available via legacy path:
  from bot.features.market.shopping import search_shopping
"""
from bot.features.shopping.engine import (  # noqa: F401
    ProductResult,
    search_shopping,
    compare_products,
    shopping_price_history,
    create_shopping_price_alert,
    list_shopping_price_alerts,
    cancel_shopping_price_alert,
    shopping_engine_status,
    check_shopping_price_alerts,
    _split_compare_query,
    _clean_query,
    _budget,
    _explicit_domain,
)

__all__ = [
    "ProductResult",
    "search_shopping",
    "compare_products",
    "shopping_price_history",
    "create_shopping_price_alert",
    "list_shopping_price_alerts",
    "cancel_shopping_price_alert",
    "shopping_engine_status",
    "check_shopping_price_alerts",
    "_split_compare_query",
    "_clean_query",
    "_budget",
    "_explicit_domain",
]
