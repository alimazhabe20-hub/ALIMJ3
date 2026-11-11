"""Legacy import path — re-exports shopping package.

Prefer:
  from bot.features.shopping import search_shopping
"""
from bot.features.shopping.engine import *  # noqa: F401,F403
from bot.features.shopping.engine import (  # noqa: F401
    search_shopping,
    compare_products,
    shopping_price_history,
    create_shopping_price_alert,
    list_shopping_price_alerts,
    cancel_shopping_price_alert,
    shopping_engine_status,
    check_shopping_price_alerts,
    ProductResult,
)
