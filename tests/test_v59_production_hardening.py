import asyncio
import os
from pathlib import Path

os.environ.setdefault("BOT_TOKEN", "v59-test-token")
os.environ.setdefault("ADMIN_IDS", "123")
os.environ.setdefault("METRICS_TOKEN", "v59-metrics-token")


def test_release_and_config_hardening():
    from bot.release import VERSION
    from bot.config import config
    assert VERSION
    assert config.HTTP_CIRCUIT_FAILURE_THRESHOLD >= 1
    assert config.HTTP_CIRCUIT_COOLDOWN >= 1
    assert config.ALERT_DEDUP_TTL >= 1


def test_alert_deduplication():
    from bot.features.market.trading_intelligence import dedupe_alerts
    dedupe_alerts._seen = {}
    assert dedupe_alerts(["volume_spike", "funding_extreme"], key="BTC|r", now=1000) == ["volume_spike", "funding_extreme"]
    assert dedupe_alerts(["volume_spike", "funding_extreme"], key="BTC|r", now=1001) == []
    assert dedupe_alerts(["volume_spike"], key="BTC|r", now=2000, ttl_seconds=900) == ["volume_spike"]


def test_adaptive_signal_dedup_and_version(tmp_path, monkeypatch):
    monkeypatch.setenv("ALIMJ_DATA_DIR", str(tmp_path))
    from bot.features.market import trading_adaptation as a
    sid1 = a.record_signal("BTC", "long", 100, regime="روند صعودی", setup="لانگ")
    sid2 = a.record_signal("BTC", "long", 100.1, regime="روند صعودی", setup="لانگ")
    assert sid1 and sid1 == sid2
    data = a._load()
    assert len(data["signals"]) == 1
    assert data["signals"][0]["model_version"] == "58.0.0-adaptive-hardened"


def test_http_circuit_opens_after_failures_and_resets(monkeypatch):
    import bot.utils.http_client as h
    async def run():
        h._CIRCUIT_STATE.clear()
        host = "example.test"
        old_threshold = h._CIRCUIT_FAILURE_THRESHOLD
        monkeypatch.setattr(h, "_CIRCUIT_FAILURE_THRESHOLD", 2)
        await h._circuit_result(host, False)
        await h._circuit_result(host, False)
        snap = h.circuit_snapshot()
        assert snap[host]["open"] is True
        try:
            await h._circuit_before(host)
        except h.UpstreamCircuitOpenError:
            pass
        else:
            raise AssertionError("circuit should be open")
        await h._circuit_result(host, True)
        assert h.circuit_snapshot()[host]["open"] is False
        h._CIRCUIT_FAILURE_THRESHOLD = old_threshold
    asyncio.run(run())
