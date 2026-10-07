"""shopping: models responsibilities."""
from .shopping_common import *  # noqa: F401,F403
from . import shopping_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


class ProductResult:
    source: str
    title: str
    url: str
    price: int | None = None
    old_price: int | None = None
    currency: str = "تومان"
    seller: str = ""
    availability: str = ""
    image: str = ""
    match_hint: str = ""
