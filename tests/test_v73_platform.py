from pathlib import Path

from bot.services.v73_platform import (
    redact_secrets, safe_archive_member, safe_path, sanitize_tool_arguments,
    safe_public_url, qa_snapshot,
)


def test_redaction():
    assert "super-secret" not in redact_secrets("api_key=super-secret")
    assert "REDACTED" in redact_secrets("Bearer abcdefghijklmnop")


def test_archive_and_path_safety(tmp_path):
    assert safe_archive_member("a/b.txt")
    assert not safe_archive_member("../../evil")
    assert safe_path(tmp_path / "x.txt", tmp_path)
    assert not safe_path(tmp_path.parent / "evil.txt", tmp_path)


def test_url_rejects_localhost():
    ok, reason = safe_public_url("http://127.0.0.1:8080")
    assert not ok
    assert reason == "private_host"


def test_argument_bounds():
    out = sanitize_tool_arguments({"x": "a" * 10000, "a": list(range(100))})
    assert len(out["x"]) == 6000
    assert len(out["a"]) == 20


def test_qa_snapshot():
    result = qa_snapshot(Path(__file__).parents[1])
    assert result["syntax_ok"]
