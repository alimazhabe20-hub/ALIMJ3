"""Shopping providers."""
from bot.features.shopping.providers.digikala import (
    _direct_digikala,
    _digikala_html_fallback,
    _digikala_product_url,
)
from bot.features.shopping.providers.torob import _direct_torob
from bot.features.shopping.providers.shopino import _direct_shopino

__all__ = [
    "_direct_digikala",
    "_digikala_html_fallback",
    "_digikala_product_url",
    "_direct_torob",
    "_direct_shopino",
]
