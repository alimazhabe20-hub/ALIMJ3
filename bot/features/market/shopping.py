"""هوش خرید بازار: جستجوی گسترده چندفروشگاهی + اینستاگرام + کل وب.

این ماژول به API خصوصی فروشگاه‌ها وابسته نیست. از موتور جستجو (DuckDuckGo)
برای فروشگاه‌های هدف، اینستاگرام و کل اینترنت استفاده می‌کند و سپس صفحه را
برای داده‌های ساختاریافته (JSON-LD Product/Offer) و الگوهای قیمت فارسی می‌خواند.
"""
from __future__ import annotations
from bot.utils.modular_loader import load_modular_part

import asyncio
import hashlib
import json
import re
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote_plus, urlparse

import httpx
from bs4 import BeautifulSoup

from bot.logger import logger

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)
SEARCH_URL = "https://html.duckduckgo.com/html/"
CACHE: dict[str, tuple[float, str]] = {}
CACHE_TTL = 150

# لیست گسترده فروشگاه‌ها و منابع ایرانی + بین‌المللی مرتبط
SOURCES = {
    # مقایسه قیمت و مارکت‌پلیس‌های اصلی
    "torob": {"label": "ترب", "domains": ["torob.com"]},
    "digikala": {"label": "دیجی‌کالا", "domains": ["digikala.com"]},
    "snappshop": {"label": "اسنپ‌شاپ", "domains": ["snappshop.ir"]},
    "emalls": {"label": "ایمالز", "domains": ["emalls.ir"]},
    "basalam": {"label": "باسلام", "domains": ["basalam.com"]},
    # تخصصی تکنولوژی و موبایل
    "technolife": {"label": "تکنولایف", "domains": ["technolife.ir"]},
    "momtaz": {"label": "مقداد آی‌تی", "domains": ["meghdadit.com"]},
    "kalaoma": {"label": "کالاوما", "domains": ["kalaoma.com"]},
    "19kala": {"label": "۱۹کالا", "domains": ["19kala.com"]},
    "mobile": {"label": "موبایل‌دات‌آی‌آر", "domains": ["mobile.ir"]},
    "digistyle": {"label": "دیجی‌استایل", "domains": ["digistyle.com"]},
    # مد و پوشاک و زیبایی
    "modiseh": {"label": "مدیسه", "domains": ["modiseh.com"]},
    "zanbil": {"label": "زنبیل", "domains": ["zanbil.ir"]},
    "goldiran": {"label": "گلدیران", "domains": ["goldiran.com"]},
    # مارکت‌پلیس و عمومی
    "alibaba": {"label": "علی‌بابا", "domains": ["alibaba.ir"]},
    "sheypoor": {"label": "شیپور", "domains": ["sheypoor.com"]},
    "divar": {"label": "دیوار", "domains": ["divar.ir"]},
    "okala": {"label": "اکالا", "domains": ["okala.com"]},
    "takhfifan": {"label": "تخفیفان", "domains": ["takhfifan.com"]},
    # اینستاگرام و شبکه‌های اجتماعی
    "instagram": {"label": "اینستاگرام", "domains": ["instagram.com"]},
    # جستجوی عمومی وب (همه‌جا)
    "general": {"label": "وب / سایر", "domains": []},
}

# کلمات کلیدی برای تقویت جستجوی اینستاگرام و فروشگاه‌های آنلاین
INSTA_KEYWORDS = [
    "فروشگاه", "شاپ", "خرید", "قیمت", "فروش آنلاین", "online shop",
    "فروشگاه اینترنتی", "خرید آنلاین",
]


load_modular_part(__file__, 'shopping_parts/part_001_ProductResult.py')


load_modular_part(__file__, 'shopping_parts/part_002__norm_digits.py')


load_modular_part(__file__, 'shopping_parts/part_003__price.py')


load_modular_part(__file__, 'shopping_parts/part_004__currency_and_price.py')


load_modular_part(__file__, 'shopping_parts/part_005__domain.py')


load_modular_part(__file__, 'shopping_parts/part_006__source_for_url.py')


load_modular_part(__file__, 'shopping_parts/part_007__clean_title.py')


load_modular_part(__file__, 'shopping_parts/part_008__search.py')


load_modular_part(__file__, 'shopping_parts/part_009__extract_jsonld.py')


load_modular_part(__file__, 'shopping_parts/part_010__from_product.py')


load_modular_part(__file__, 'shopping_parts/part_011__inspect.py')


load_modular_part(__file__, 'shopping_parts/part_012__query_variants.py')


load_modular_part(__file__, 'shopping_parts/part_013__score.py')


load_modular_part(__file__, 'shopping_parts/part_014__save_history.py')


load_modular_part(__file__, 'shopping_parts/part_015_shopping_price_history.py')


load_modular_part(__file__, 'shopping_parts/part_016_search_shopping.py')
