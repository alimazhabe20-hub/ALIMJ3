"""متریک ساده پاسخ‌های گروهی برای مانیتورینگ سرعت و کیفیت."""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Dict

_stats: Dict[str, float] = defaultdict(float)
_counts: Dict[str, int] = defaultdict(int)


def mark(event: str, duration: float | None = None) -> None:
    _counts[event] += 1
    if duration is not None:
        _stats[event + "_ms_sum"] += duration * 1000
        _stats[event + "_ms_n"] += 1


def snapshot() -> dict:
    out = dict(_counts)
    for k, v in list(_stats.items()):
        if k.endswith("_ms_sum"):
            base = k[: -len("_ms_sum")]
            n = _stats.get(base + "_ms_n", 0) or 1
            out[base + "_avg_ms"] = round(v / n, 1)
    return out


class Timer:
    def __init__(self, event: str):
        self.event = event
        self.t0 = 0.0

    def __enter__(self):
        self.t0 = time.perf_counter()
        return self

    def __exit__(self, *args):
        mark(self.event, time.perf_counter() - self.t0)
