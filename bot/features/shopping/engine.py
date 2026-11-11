"""Shopping engine — compatibility module.

Implementation is split across:
  - shared.py (orchestration, ranking, history)
  - providers/digikala.py
  - providers/torob.py
"""
from bot.features.shopping.shared import *  # noqa: F401,F403
from bot.features.shopping.shared import (  # noqa: F401
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
    _direct_digikala,
    _direct_torob,
)
