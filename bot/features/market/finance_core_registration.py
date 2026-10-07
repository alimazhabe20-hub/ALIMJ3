"""Late registration/compatibility actions for finance_core."""
from .finance_core_common import *  # noqa
from . import finance_core_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


_FA_CURRENCY = {
    "دلار": "usd", "دلارآمریکا": "usd", "usd": "usd", "dollar": "usd", "دلاری": "usd",
    "یورو": "eur", "euro": "eur", "eur": "eur",
    "پوند": "gbp", "pound": "gbp", "gbp": "gbp",
    "تومان": "toman", "تومن": "toman", "tmn": "toman",
    "ریال": "rial", "irr": "rial",
    "درهم": "aed", "aed": "aed",
    "لیر": "try", "try": "try",
    "یوان": "cny", "cny": "cny",
    "روبل": "rub", "rub": "rub",
    "بیتکوین": "btc", "بیت‌کوین": "btc", "بیت کوین": "btc",
    "اتریوم": "eth", "تتر": "usdt", "تون": "ton", "سولانا": "sol",
    "کاردانو": "ada", "ریپل": "xrp", "دوج": "doge", "دوج‌کوین": "doge",
}
