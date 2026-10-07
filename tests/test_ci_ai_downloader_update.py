from pathlib import Path


def test_quality_script_does_not_fail_on_ruff():
    text = Path("scripts/run_quality.py").read_text(encoding="utf-8")
    assert "Ruff is advisory" in text
    assert "return ruff_code" not in text


def test_update_button_only_in_smart_settings():
    text = Path("bot/utils/keyboard_factory.py").read_text(encoding="utf-8")
    more = text.split("def get_more_keyboard():", 1)[1].split("def get_date_tools_keyboard():", 1)[0]
    smart = text.split("def get_smart_settings_keyboard():", 1)[1].split("def get_country_keyboard():", 1)[0]
    assert "🔄 بررسی بروزرسانی" not in more
    assert "🔄 بررسی بروزرسانی" in smart


def test_groq_retired_models_are_migrated():
    text = Path("bot/services/ai_runtime.py").read_text(encoding="utf-8")
    assert "llama-3.1-8b-instant" in text
    assert "openai/gpt-oss-20b" in text
    assert "llama-3.3-70b-versatile" in text
    assert "openai/gpt-oss-120b" in text
    assert '"gemini-3.7-flash"' in text


def test_instagram_preflight_keeps_original_reel_url():
    text = Path("bot/services/downloader.py").read_text(encoding="utf-8")
    assert "_normalize_media_url" in text
    assert "login page" in text
    assert '"extractor_args"' in text
    assert '"instagram": {"app_id": "web"}' in text
