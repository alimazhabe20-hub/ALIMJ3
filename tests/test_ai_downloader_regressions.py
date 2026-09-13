from pathlib import Path


def test_update_center_only_in_smart_settings():
    text = Path("bot/utils/keyboard_factory.py").read_text(encoding="utf-8")
    more = text.split("def get_more_keyboard():", 1)[1].split("def get_date_tools_keyboard():", 1)[0]
    smart = text.split("def get_smart_settings_keyboard():", 1)[1].split("def get_country_keyboard():", 1)[0]
    assert "🔄 بررسی بروزرسانی" not in more
    assert smart.count("🔄 بررسی بروزرسانی") == 1


def test_simple_ai_prompt_does_not_enable_tools():
    text = Path("bot/services/ai_providers.py").read_text(encoding="utf-8")
    assert "def _prompt_needs_tools" in text
    assert "use_tools = use_tools and _prompt_needs_tools(prompt)" in text


def test_groq_deprecated_models_are_migrated():
    text = Path("bot/services/ai_runtime.py").read_text(encoding="utf-8")
    assert '"llama-3.1-8b-instant": "openai/gpt-oss-20b"' in text
    assert '"llama-3.3-70b-versatile": "openai/gpt-oss-120b"' in text


def test_instagram_skips_generic_redirect_preflight():
    text = Path("bot/services/downloader.py").read_text(encoding="utf-8")
    assert "if _is_instagram_url(current):" in text
    assert 'return current' in text
    assert '"extractor_args": {"instagram": {"app_id": "web"}}' in text
    assert "Never treat an Instagram HTML/login/challenge page" in text
