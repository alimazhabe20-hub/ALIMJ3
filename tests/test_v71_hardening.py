import os
os.environ.setdefault("BOT_TOKEN", "test-token")

from bot.services.downloader import is_url, _safe_name, _classify_error
from bot.services.v71_platform import (
    detect_language, security_check_url, auto_recovery_policy, ai_route_hint,
    init_v71_tables, self_test,
)


def test_downloader_safety_and_errors():
    assert is_url("https://example.com/file.mp4")
    assert not is_url("file:///etc/passwd")
    assert _safe_name('../x:y?.mp4').endswith('.mp4')
    assert _classify_error('HTTP 429 Too Many Requests') == 'rate_limited'
    assert _classify_error('403 forbidden captcha') == 'site_blocked'


def test_security_blocks_private_targets_without_network():
    assert security_check_url("http://127.0.0.1")["ok"] is False
    assert security_check_url("http://10.0.0.1")["ok"] is False


def test_platform_runtime_contracts():
    init_v71_tables()
    assert detect_language("hello world") == "en"
    assert detect_language("سلام دنیا") == "fa"
    assert auto_recovery_policy("timeout", 0)["retry"] is True
    assert auto_recovery_policy("fatal", 0)["retry"] is False
    assert ai_route_hint("hi")["mode"] == "fast"
    assert isinstance(self_test(), dict)
