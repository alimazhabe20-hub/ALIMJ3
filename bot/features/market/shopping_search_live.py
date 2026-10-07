"""Compatibility facade for the refactored live shopping implementation."""
from .shopping_search import search_shopping
from .shopping_parser import (_digits, _budget, _is_phone, _explicit_domain, _is_foreign_explicit, _strip_site_words, _parse_price, _price_from_text, _title_ok)
from .shopping_provider import _bing_search, _direct_torob, _direct_digikala
from .shopping_formatter import format_shopping_results
__all__ = ["search_shopping"]
