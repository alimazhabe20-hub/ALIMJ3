import os, tempfile


def test_adaptive_record_settle_and_profile(monkeypatch):
    from bot.features.market import trading_adaptation as a
    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setenv("ALIMJ_DATA_DIR", td)
        sid=a.record_signal("BTC", "long", 100, 98, 105, "روند صعودی", 75, 80, {"trend":80}, horizon_seconds=60)
        assert sid
        assert a.settle_signals("BTC", 102, now=10**12) == 1
        p=a.adaptive_profile("BTC", "روند صعودی", "default")
        assert p["samples"] == 1
        assert p["win_rate"] == 100.0


def test_adaptive_weight_adjustment_needs_enough_samples(monkeypatch):
    from bot.features.market import trading_adaptation as a
    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setenv("ALIMJ_DATA_DIR", td)
        base={"trend":0.5,"momentum":0.5}
        assert a.adaptive_weights(base, "BTC", "رنج", "default") == base
