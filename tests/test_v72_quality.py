import os
os.environ.setdefault("BOT_TOKEN", "test-token")

from bot.services.v72_platform import (
    normalize_download_mode, ytdlp_format, progress_percent,
    classify_ai_complexity, route_candidates, dedupe_sources,
    extract_document, document_context, safe_web_url,
)


def test_downloader_quality_modes():
    assert normalize_download_mode("1080") == "1080p"
    assert normalize_download_mode("mp3") == "audio"
    assert "height<=720" in ytdlp_format("720p")
    assert progress_percent(5, 10) == 50.0


def test_ai_router_is_deterministic():
    assert classify_ai_complexity("hi") == "fast"
    rows = route_candidates("compare these complex documents", [("fast", "instant"), ("quality", "70b")])
    assert rows and rows[0].provider == "quality"


def test_web_dedupe_and_ssrf():
    assert safe_web_url("https://example.com/a") == "https://example.com/a"
    rows = dedupe_sources([{"url":"https://example.com/a","score":.2},{"url":"https://example.com/a","score":.9}])
    assert len(rows) == 1


def test_document_text_and_prompt_boundary():
    doc = extract_document(b"hello world", "note.txt", "text/plain")
    assert doc["kind"] == "text"
    assert "UNTRUSTED DOCUMENT DATA" in document_context(doc)
