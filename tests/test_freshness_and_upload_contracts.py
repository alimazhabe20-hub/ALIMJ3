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
    assert "current as of" in text


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
