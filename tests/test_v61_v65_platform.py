import os, tempfile
os.environ.setdefault('BOT_TOKEN','test-token')
os.environ.setdefault('DB_PATH', os.path.join(tempfile.gettempdir(),'alimj3_v65_test.db'))
from bot.services.v61_v65_platform import detect_language, classify_intent, RequestQueue, features_snapshot

def test_languages_only_three(): assert detect_language('hello')=='en'; assert detect_language('مرحبا كيف حالك')=='ar'; assert detect_language('سلام خوبی')=='fa'
def test_intents(): assert classify_intent('قیمت بیت کوین چنده')=='crypto_price'; assert classify_intent('لینک خرید گوشی')=='product_search'; assert classify_intent('جستجو درباره طلا')=='web_search'
def test_features_free_and_three_lang():
    x=features_snapshot(); assert x['free'] and not x['subscriptions'] and x['languages']==['fa','en','ar']
def test_queue():
    q=RequestQueue(2,4); assert q.pending==0
