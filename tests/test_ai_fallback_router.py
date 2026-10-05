def test_unknown_capability_uses_api_hub_fallback():
    import bot.services.ai_tools
    from bot.services.tool_runtime import select_capability_tool

    assert select_capability_tool("یک موضوع ناشناخته درباره فلسفه بگو") == "hub_smart_public_api"


def test_news_request_prefers_web_search():
    import bot.services.ai_tools
    from bot.services.tool_runtime import select_capability_tool

    assert select_capability_tool("آخرین خبرهای امروز درباره فناوری چیست؟") == "web_search"
