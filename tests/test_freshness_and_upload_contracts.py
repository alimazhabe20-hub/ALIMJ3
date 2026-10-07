from pathlib import Path


def test_live_router_requires_tools_for_time_sensitive_requests():
    import bot.services.ai_tools  # registers built-in tools
    from bot.services.tool_runtime import select_capability_tool

    assert select_capability_tool("قیمت آیفون 18 پرو مکس چنده؟") == "search_shopping"
    assert select_capability_tool("آخرین اخبار آیفون 18 چیست؟") == "web_search"
    assert select_capability_tool("قیمت بیت کوین الان چنده؟") == "get_crypto_price"
    assert select_capability_tool("هوای تهران امروز چطوره؟") == "get_weather"
    assert select_capability_tool("فلسفه چیست؟") == "hub_smart_public_api"


def test_web_search_is_marked_live_and_has_no_stale_fallback():
    text = Path("bot/services/ai_extras_parts/part_011_web_search.py").read_text(encoding="utf-8")
    assert "LIVE_WEB_RESULTS" in text
    assert "LIVE_DATA_UNAVAILABLE" in text
    # v79: the query must be sent as-is (no "(current as of ...)" suffix) and
    # real search APIs must be supported with a keyless fallback.
    assert "current as of" not in text.replace("Older versions appended \"(current as of DATE)\"", "")
    for provider in ("TAVILY_API_KEY", "BRAVE_API_KEY", "SERPER_API_KEY", "SEARXNG_URL", "duckduckgo"):
        assert provider in text


def test_telegram_upload_defaults_are_safe_without_local_api():
    from bot.services.telegram_upload import STANDARD_MAX_UPLOAD_BYTES, LOCAL_MAX_UPLOAD_BYTES
    assert STANDARD_MAX_UPLOAD_BYTES < 50 * 1024 * 1024
    assert LOCAL_MAX_UPLOAD_BYTES >= 1024 * 1024 * 1024


def test_release_metadata_uses_one_runtime_version():
    import re
    release = Path("bot/release.py").read_text(encoding="utf-8")
    render = Path("render.yaml").read_text(encoding="utf-8")
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")
    version = re.search(r'VERSION\s*=\s*"([^"]+)"', release).group(1)
    assert f'value: "{version}"' in render
    assert f'image: alimj:{version}' in compose
    assert f'RELEASE_VERSION: "{version}"' in compose


def test_v79_freshness_catches_recommendation_and_spec_requests():
    from bot.services.ai_freshness import classify

    shopping = [
        "یه گوشی موبایل تا 50 میلیون پیدا کن برام",
        "یه گوشی موبایل تا ۵۰ میلیون پیدا کن",
        "بهترین گوشی زیر ۵۰ میلیون کدومه",
        "لپتاپ گیمینگ پیشنهاد بده",
        "یه ماشین لباسشویی ارزون پیشنهاد بده",
    ]
    for q in shopping:
        d = classify(q)
        assert d.required and d.tool == "search_shopping", q

    web = [
        "آیفون ۱۶ چه مشخصاتی داره",
        "مدل جدید ps5 چیه",
        "بهترین مدل هوش مصنوعی کدومه",
        "رئیس جمهور آمریکا کیه",
        "نتیجه بازی پرسپولیس دیشب",
    ]
    for q in web:
        d = classify(q)
        assert d.required and d.tool == "web_search", q


def test_v79_freshness_does_not_over_trigger():
    from bot.services.ai_freshness import classify

    for q in ("سلام", "یه جوک بگو", "فلسفه چیست؟", "تاریخچه جنگ جهانی دوم",
              "تاریخ ایران رو توضیح بده", "رنگ طلایی چطوره", "هواپیما چطوری پرواز میکنه",
              "یه کد پایتون برای مرتب‌سازی بنویس"):
        assert not classify(q).required, q


def test_v79_substring_false_positives_fixed():
    from bot.services.ai_freshness import classify

    # «ارزون» must not be treated as currency («ارز»); «هواوی» is not weather.
    assert classify("یه ماشین لباسشویی ارزون پیشنهاد بده").tool == "search_shopping"
    assert classify("گوشی هواوی خوب پیشنهاد بده").tool == "search_shopping"
    # «الان ... چنده» about prices must not become a clock question.
    assert classify("قیمت بیت کوین الان چنده؟").tool != "get_current_datetime"
    assert classify("تاریخ امروز چنده").tool == "get_current_datetime"
