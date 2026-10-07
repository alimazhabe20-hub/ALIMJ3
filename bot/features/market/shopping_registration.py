"""Late registration/compatibility actions for shopping."""
from .shopping_common import *  # noqa
from . import shopping_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


if TYPE_CHECKING:
    from bot.features.market.shopping import ProductResult

if TYPE_CHECKING:
    from bot.features.market.shopping import ProductResult

if TYPE_CHECKING:
    from bot.features.market.shopping import ProductResult

_SITE_ALIASES = {
    "دیجی کالا": "digikala.com", "دیجی‌کالا": "digikala.com", "digikala": "digikala.com",
    "ترب": "torob.com", "torob": "torob.com",
    "ایمالز": "emalls.ir", "emalls": "emalls.ir",
    "تکنولایف": "technolife.ir", "technolایف": "technolife.ir", "technolife": "technolife.ir",
    "اسنپ شاپ": "snapp.shop", "اسنپ‌شاپ": "snapp.shop", "snappshop": "snapp.shop",
    "باسلام": "basalam.com", "basalam": "basalam.com",
    "دیجی استایل": "digistyle.com", "دیجی‌استایل": "digistyle.com", "digistyle": "digistyle.com",
    "موبایل دات آی آر": "mobile.ir", "mobile.ir": "mobile.ir",
    "آمازون": "amazon.com", "amazon": "amazon.com",
    "ebay": "ebay.com", "ایبی": "ebay.com",
    "علی اکسپرس": "aliexpress.com", "علی‌اکسپرس": "aliexpress.com", "aliexpress": "aliexpress.com",
    "walmart": "walmart.com", "وال مارت": "walmart.com",
    "bestbuy": "bestbuy.com", "best buy": "bestbuy.com",
    "etsy": "etsy.com", "اتسی": "etsy.com",
    "newegg": "newegg.com",
    "noon": "noon.com", "نون": "noon.com",
    "temu": "temu.com", "تیمو": "temu.com",
    "shein": "shein.com", "شین": "shein.com",
    "nike": "nike.com", "نایکی": "nike.com",
    "adidas": "adidas.com", "آدیداس": "adidas.com",
}
