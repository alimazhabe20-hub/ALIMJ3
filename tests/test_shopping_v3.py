import os
os.environ.setdefault('BOT_TOKEN', '123:TEST')
os.environ.setdefault('ADMIN_IDS', '1')

from bot.features.market.shopping_parts import part_016_search_shopping_live as shop
from bot.handlers.messages_parts import part_005__handle_special_ai_intents as intents


def test_budget_parsing():
    assert shop._budget('گوشی تا 50 میلیون') == 50_000_000
    assert shop._budget('کفش زیر 3 میلیون تومان') == 3_000_000
    assert shop._budget('کالا تا 50000000 تومان') == 50_000_000


def test_generic_product_request_is_live():
    assert intents.is_live_product_request('یه جوراب مردانه پیدا کن برام') is True
    assert intents.is_live_product_request('یه کفش مردانه پیدا کن') is True
    assert intents.is_live_product_request('گوشی سامسونگ تا 50 میلیون') is True
    assert intents.is_live_product_request('قیمت دلار چنده؟') is False


def test_foreign_is_opt_in():
    assert shop._foreign_requested('یه کفش پیدا کن') is False
    assert shop._foreign_requested('سایت های خارجی هم بگرد') is True
    assert shop._explicit_domain('از Amazon هم بگرد') == 'amazon.com'


def test_query_does_not_become_generic_when_budgeted():
    variants = shop._query_variants('جوراب مردانه', 1_000_000)
    assert any('جوراب مردانه' in x for x in variants)
    assert not any('وسایل کاربردی' in x for x in variants)
